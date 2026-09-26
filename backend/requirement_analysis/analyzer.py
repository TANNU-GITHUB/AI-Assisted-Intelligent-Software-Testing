"""Task 4 — Requirement analysis via Gemini: natural language → structured testable rules."""

from __future__ import annotations

import json
import re
from typing import Any

from config import GEMINI_API_KEY, GEMINI_MODEL
from input_handler.handler import load_session, save_session, session_dir
from requirement_analysis.prompts import PROMPT_TEMPLATE, STRICT_RETRY_PROMPT


class RequirementAnalysisError(ValueError):
    """Raised when the LLM cannot produce valid structured requirements."""


def _extract_json(text: str) -> Any:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise json.JSONDecodeError("No JSON object found", cleaned, 0)
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def _normalize(data: Any) -> list[dict[str, str]]:
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("requirements")
        if items is None:
            raise RequirementAnalysisError("JSON is missing a 'requirements' array.")
    else:
        raise RequirementAnalysisError("JSON root must be an object or array.")

    if not isinstance(items, list) or not items:
        raise RequirementAnalysisError("No testable requirements were extracted.")

    normalized: list[dict[str, str]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise RequirementAnalysisError("Each requirement must be a JSON object.")
        condition = str(item.get("condition") or "").strip()
        expected = str(item.get("expected_result") or item.get("expected") or "").strip()
        if not condition or not expected:
            raise RequirementAnalysisError(
                "Each requirement needs both 'condition' and 'expected_result'."
            )
        req_id = str(item.get("requirement_id") or f"REQ-{index:02d}").strip()
        if not re.fullmatch(r"REQ-\d+", req_id, flags=re.IGNORECASE):
            req_id = f"REQ-{index:02d}"
        else:
            req_id = f"REQ-{int(req_id.split('-')[1]):02d}"
        normalized.append(
            {
                "requirement_id": req_id,
                "condition": condition,
                "expected_result": expected,
                "source_excerpt": str(item.get("source_excerpt") or "").strip(),
            }
        )

    # Guarantee unique sequential IDs even if the model duplicated them.
    for index, item in enumerate(normalized, start=1):
        item["requirement_id"] = f"REQ-{index:02d}"
    return normalized


def _call_gemini(prompt: str, api_key: str, model_name: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise RequirementAnalysisError("Gemini returned an empty response.")
    return text


def analyze_requirements(
    requirements_text: str,
    *,
    api_key: str | None = None,
    model_name: str | None = None,
    llm_call=_call_gemini,
) -> dict[str, Any]:
    key = (api_key if api_key is not None else GEMINI_API_KEY).strip()
    model = model_name or GEMINI_MODEL
    if not key or key == "your_gemini_api_key_here":
        raise RequirementAnalysisError(
            "GEMINI_API_KEY is missing. Paste it into backend/.env as GEMINI_API_KEY=..."
        )

    text = requirements_text.strip()
    if not text:
        raise RequirementAnalysisError("Requirements text cannot be empty.")

    first_prompt = PROMPT_TEMPLATE.format(requirements_text=text)
    try:
        raw = llm_call(first_prompt, key, model)
        items = _normalize(_extract_json(raw))
    except (json.JSONDecodeError, RequirementAnalysisError, TypeError, ValueError):
        retry_prompt = STRICT_RETRY_PROMPT.format(requirements_text=text)
        try:
            raw = llm_call(retry_prompt, key, model)
            items = _normalize(_extract_json(raw))
        except (json.JSONDecodeError, RequirementAnalysisError, TypeError, ValueError) as exc:
            raise RequirementAnalysisError(
                "Gemini did not return valid JSON after one retry. "
                f"Last error: {exc}"
            ) from exc

    return {
        "model": model,
        "requirement_count": len(items),
        "requirements": items,
    }


def analyze_session_requirements(session_id: str) -> dict[str, Any]:
    payload = load_session(session_id)
    requirements_path = session_dir(session_id) / "requirements.txt"
    requirements_text = requirements_path.read_text(encoding="utf-8")
    analysis = analyze_requirements(requirements_text)
    payload["requirement_analysis"] = analysis
    payload["status"] = (
        "ready_for_test_generation"
        if payload.get("code_analysis")
        else "requirements_analyzed"
    )
    return save_session(payload)
