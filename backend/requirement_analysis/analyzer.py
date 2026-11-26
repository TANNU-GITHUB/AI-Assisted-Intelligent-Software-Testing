"""Task 4 — Requirement analysis via LLM: natural language → structured testable rules."""

from __future__ import annotations

import re
from typing import Any

from config import NVIDIA_API_KEY, NVIDIA_MODEL
from llm_client import generate_text
from input_handler.handler import load_session, save_session, session_dir, session_locked
from json_utils import extract_json as _extract_json
from requirement_analysis.prompts import PROMPT_TEMPLATE, STRICT_RETRY_PROMPT


class RequirementAnalysisError(ValueError):
    """Raised when the LLM cannot produce valid structured requirements."""


def _normalize(data: Any) -> list[dict[str, str]]:
    candidate_keys = (
        "requirements",
        "testable_scenarios",
        "scenarios",
        "rules",
        "test_cases",
        "cases",
        "specifications",
        "items",
        "steps",
        "flowchart",
        "flows",
        "requirements_list",
    )
    items: Any = None
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in candidate_keys:
            val = data.get(key)
            if isinstance(val, list) and val:
                items = val
                break

        if items is None:
            for val in data.values():
                if isinstance(val, dict):
                    for key in candidate_keys:
                        nested_val = val.get(key)
                        if isinstance(nested_val, list) and nested_val:
                            items = nested_val
                            break
                    if items is not None:
                        break

        if items is None:
            if any(k in data for k in ("condition", "if", "when", "trigger")) and any(
                k in data for k in ("expected_result", "expected", "then", "outcome", "result")
            ):
                items = [data]

        if items is None:
            for val in data.values():
                if isinstance(val, list) and val and isinstance(val[0], dict):
                    items = val
                    break

        if items is None and data and all(isinstance(v, dict) for v in data.values()):
            items = list(data.values())

        if items is None:
            raise RequirementAnalysisError("JSON is missing a 'requirements' array.")
    else:
        raise RequirementAnalysisError("JSON root must be an object or array.")

    if not isinstance(items, list) or not items:
        raise RequirementAnalysisError("No testable requirements were extracted.")

    normalized: list[dict[str, str]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            if isinstance(item, str) and item.strip():
                item = {"condition": item.strip()}
            else:
                continue
        condition = str(
            item.get("condition")
            or item.get("if")
            or item.get("when")
            or item.get("trigger")
            or item.get("input")
            or item.get("description")
            or item.get("rule")
            or item.get("scenario")
            or ""
        ).strip()
        expected = str(
            item.get("expected_result")
            or item.get("expected")
            or item.get("then")
            or item.get("outcome")
            or item.get("output")
            or item.get("result")
            or ""
        ).strip()

        if condition and not expected:
            if " then " in condition.lower():
                parts = re.split(r"\s+then\s+", condition, flags=re.IGNORECASE, maxsplit=1)
                condition = parts[0].strip()
                if condition.lower().startswith("if "):
                    condition = condition[3:].strip()
                expected = parts[1].strip()
            elif "->" in condition:
                parts = condition.split("->", 1)
                condition = parts[0].strip()
                expected = parts[1].strip()
            elif "=>" in condition:
                parts = condition.split("=>", 1)
                condition = parts[0].strip()
                expected = parts[1].strip()
            else:
                expected = "expected outcome is satisfied"

        if not condition or not expected:
            continue
        if condition in {"...", "plain-language IF condition that can be checked"}:
            continue
        if expected in {"...", "plain-language THEN expected outcome"}:
            continue

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

    if not normalized:
        raise RequirementAnalysisError("No testable requirements were extracted.")

    # Guarantee unique sequential IDs even if the model duplicated them.
    for index, item in enumerate(normalized, start=1):
        item["requirement_id"] = f"REQ-{index:02d}"
    return normalized


def _heuristic_requirements(requirements_text: str) -> list[dict[str, str]]:
    """Split requirements into structured rules when the LLM is unavailable."""
    raw_lines = [line.strip() for line in requirements_text.splitlines() if line.strip()]
    lines = [l for l in raw_lines if not l.lower().startswith("pdf page")]
    if lines:
        items: list[dict[str, str]] = []
        for index, chunk in enumerate(lines[:24], start=1):
            cond = chunk
            exp = chunk
            if " then " in chunk.lower():
                parts = re.split(r"\s+then\s+", chunk, flags=re.IGNORECASE, maxsplit=1)
                cond = parts[0].strip()
                if cond.lower().startswith("if "):
                    cond = cond[3:].strip()
                exp = parts[1].strip()
            items.append(
                {
                    "requirement_id": f"REQ-{index:02d}",
                    "condition": cond,
                    "expected_result": exp,
                    "source_excerpt": chunk[:240],
                }
            )
        return items
    chunks = [
        re.sub(r"\s+", " ", part).strip(" \t-•*")
        for part in re.split(r"[\n.;]+", requirements_text)
        if part.strip()
    ]
    if not chunks:
        chunks = [requirements_text.strip() or "Unspecified behavior"]
    items: list[dict[str, str]] = []
    for index, chunk in enumerate(chunks[:24], start=1):
        items.append(
            {
                "requirement_id": f"REQ-{index:02d}",
                "condition": chunk,
                "expected_result": chunk,
                "source_excerpt": chunk[:240],
            }
        )
    return items


def _call_llm(prompt: str, api_key: str, model_name: str) -> str:
    text, model_used = generate_text(prompt, api_key=api_key, model_name=model_name)
    _call_llm.last_model_used = model_used
    return text


def analyze_requirements(
    requirements_text: str,
    *,
    api_key: str | None = None,
    model_name: str | None = None,
    llm_call=_call_llm,
) -> dict[str, Any]:
    key = (api_key if api_key is not None else NVIDIA_API_KEY).strip()
    model = model_name or NVIDIA_MODEL

    text = requirements_text.strip()
    if not text:
        raise RequirementAnalysisError("Requirements text cannot be empty.")
    if len(text) > 12_000:
        text = text[:12_000] + "\n# ... (requirements truncated for LLM context) ..."

    first_prompt = PROMPT_TEMPLATE.replace("{requirements_text}", text)
    retry_prompt = STRICT_RETRY_PROMPT.replace("{requirements_text}", text)

    def _run_prompt(prompt: str) -> list[dict[str, str]]:
        raw = llm_call(prompt, key, model)
        return _normalize(_extract_json(raw))

    fallback_reason = None
    try:
        items = _run_prompt(first_prompt)
    except Exception as exc:  # noqa: BLE001
        try:
            items = _run_prompt(retry_prompt)
        except Exception as retry_exc:  # noqa: BLE001
            items = _heuristic_requirements(text)
            fallback_reason = str(retry_exc) or str(exc)

    # Ensure no distinct requirement lines are dropped if the model returned only a subset
    text_lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#") and not l.lower().startswith("pdf page")]
    if len(text_lines) > len(items) and len(text_lines) >= 2:
        missing_lines = []
        for line in text_lines:
            low_line = line.lower()
            if not any(
                low_line in (item.get("condition", "") + " " + item.get("source_excerpt", "") + " " + item.get("expected_result", "")).lower()
                for item in items
            ):
                missing_lines.append(line)
        if missing_lines:
            heuristic_extras = _heuristic_requirements("\n".join(missing_lines))
            for h in heuristic_extras:
                items.append(h)
            for idx, item in enumerate(items, start=1):
                item["requirement_id"] = f"REQ-{idx:02d}"

    model_used = (
        getattr(_call_llm, "last_model_used", model)
        if llm_call is _call_llm and not fallback_reason
        else ("heuristic-fallback" if fallback_reason else model)
    )

    result = {
        "model": model_used,
        "requirement_count": len(items),
        "requirements": items,
    }
    if fallback_reason:
        result["fallback_reason"] = fallback_reason
    return result


@session_locked
def analyze_session_requirements(session_id: str) -> dict[str, Any]:
    payload = load_session(session_id)
    requirements_path = session_dir(session_id) / "requirements.txt"
    requirements_text = requirements_path.read_text(encoding="utf-8")
    try:
        analysis = analyze_requirements(requirements_text)
    except Exception as exc:  # noqa: BLE001
        items = _heuristic_requirements(requirements_text)
        analysis = {
            "model": "heuristic-fallback",
            "requirement_count": len(items),
            "requirements": items,
            "fallback_reason": str(exc),
        }
    payload["requirement_analysis"] = analysis
    payload["status"] = (
        "ready_for_test_generation"
        if payload.get("code_analysis")
        else "requirements_analyzed"
    )
    return save_session(payload)
