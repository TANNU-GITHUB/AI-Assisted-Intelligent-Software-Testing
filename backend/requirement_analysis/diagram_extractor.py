"""Extract testable requirements from a diagram, flowchart, or pseudocode image."""

from __future__ import annotations

import json
import re

from llm_client import LLMError, generate_from_image
from requirement_analysis.analyzer import RequirementAnalysisError, _normalize


class DiagramExtractionError(RuntimeError):
    """Raised when visual content could not be read into useful requirements."""


DIAGRAM_PROMPT = """\
You are a software test analyst. The image shows a diagram, flowchart, UML diagram, \
or pseudocode describing software behaviour. It may be a photo or scan.

Extract all discrete, testable scenarios visible in the image.

Return ONLY valid JSON (no markdown fences, no commentary):
{
  "requirements": [
    {
      "requirement_id": "REQ-01",
      "condition": "plain-language IF condition that can be checked",
      "expected_result": "plain-language THEN expected outcome",
      "source_excerpt": "brief description of which shape, branch, or pseudocode line this came from"
    }
  ]
}

Rules:
- requirement_id must be REQ-01, REQ-02, ... in order.
- Each item must be independently testable.
- Capture every decision branch, loop, state transition, and flow path shown.
- Turn pseudocode decisions into the same IF / THEN requirements.
- Do not invent behaviour that is not visible.
"""

TRANSCRIBE_PROMPT = """\
You are reading one figure or page from a software requirements document.
It may be a flowchart, UML diagram, pseudocode, scanned text, or a mix of those.

Transcribe it so a tester can use it:
- Flowcharts and diagrams: one line per path, written as "If <condition>, then <expected result>."
- Pseudocode: keep the decisions, loops, and outcomes in order, in plain language.
- Scanned or pictured sentences: transcribe the wording faithfully.

Return plain text only. Do not invent steps that are not visible. Do not use markdown fences.
"""


def transcribe_visual_content(image_bytes: bytes, mime_type: str) -> str:
    """Read a diagram, pseudocode image, or scanned page into plain text."""
    text, _model = generate_from_image(image_bytes, mime_type, TRANSCRIBE_PROMPT)
    return text.strip()


def _format_raw_as_plain_text(raw: str) -> str:
    from json_utils import extract_json as _extract_json

    text = raw.strip()
    try:
        data = _extract_json(text)
        if isinstance(data, (dict, list)):
            lines = []
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, str) and v.strip():
                        lines.append(f"{k}: {v.strip()}")
                    elif isinstance(v, list):
                        for elem in v:
                            if isinstance(elem, str) and elem.strip():
                                lines.append(elem.strip())
                            elif isinstance(elem, dict):
                                c = (
                                    elem.get("condition")
                                    or elem.get("description")
                                    or elem.get("rule")
                                )
                                e = (
                                    elem.get("expected_result")
                                    or elem.get("expected")
                                    or elem.get("then")
                                )
                                if c and e:
                                    lines.append(f"If {c}, then {e}.")
                                elif c:
                                    lines.append(str(c))
            elif isinstance(data, list):
                for elem in data:
                    if isinstance(elem, str) and elem.strip():
                        lines.append(elem.strip())
                    elif isinstance(elem, dict):
                        c = elem.get("condition") or elem.get("description") or elem.get("rule")
                        e = elem.get("expected_result") or elem.get("expected") or elem.get("then")
                        if c and e:
                            lines.append(f"If {c}, then {e}.")
                        elif c:
                            lines.append(str(c))
            joined = "\n".join(lines).strip()
            if joined:
                return joined
    except Exception:
        pass

    # Extract structured condition / expected pairs from reasoning text
    pairs = re.findall(
        r'(?:REQ-\d+.*?|(?:\d+\.))?\s*Condition:\s*(?:IF\s*)?([^\n\r]+)[\r\n]+\s*(?:\*\s*)?Expected(?:\s*Result)?:\s*(?:THEN\s*)?([^\n\r]+)',
        text,
        flags=re.IGNORECASE,
    )
    if pairs:
        clean_reqs: list[str] = []
        seen: set[tuple[str, str]] = set()
        for cond, exp in pairs:
            c = cond.strip().rstrip(".").strip()
            e = exp.strip().rstrip(".").strip()
            key = (c.lower(), e.lower())
            if key not in seen and len(c) > 2 and len(e) > 2:
                seen.add(key)
                clean_reqs.append(f"REQ-{len(clean_reqs)+1:02d}: If {c}, then {e}.")
        if clean_reqs:
            return "\n".join(clean_reqs)

    clean_lines: list[str] = []
    for line in text.splitlines():
        l = line.strip()
        if not l or len(l) < 4:
            continue
        low = l.lower()
        if any(low.startswith(p) for p in [
            "the user wants", "i need to", "the json structure", "each requirement needs",
            "let's analyze", "here's a thinking process", "respond with valid json",
            "rules:", "return only", "natural language", "structured requirements",
            "this is tricky", "i think the safest", "final json", "wait, the prompt",
            "decision diamond", "process box"
        ]):
            continue
        clean_lines.append(l)

    joined_clean = "\n".join(clean_lines[:25]).strip()
    clean = re.sub(r"```[a-zA-Z0-9_-]*\n?", "", joined_clean).strip()
    clean = clean.strip("`").strip()
    if clean in ("{}", "[]", '{"requirements": []}', '{"requirements":[]}', '{"requirements": null}'):
        return ""
    return clean


def extract_requirements_from_diagram(image_bytes: bytes, mime_type: str) -> dict:
    """Use a vision LLM to extract structured requirements from a diagram image.

    Returns a dict with keys: model, requirement_count, requirements, source.
    When the model returns usable prose instead of JSON, that prose is kept
    as plain_text.
    """
    from json_utils import extract_json as _extract_json

    try:
        raw, model_used = generate_from_image(image_bytes, mime_type, DIAGRAM_PROMPT)
    except LLMError as exc:
        raise DiagramExtractionError(
            "Could not analyze the image with a vision model. Check NVIDIA "
            "vision access or configure Ollama with llava, then try again. "
            f"Details: {exc}"
        ) from exc

    try:
        items = _normalize(_extract_json(raw))
    except (json.JSONDecodeError, RequirementAnalysisError) as exc:
        plain = _format_raw_as_plain_text(raw)
        if not plain:
            raise DiagramExtractionError(
                f"The vision model did not return usable requirements: {exc}"
            ) from exc

        # Extract structured requirements if plain text contains condition/then lines
        lines = [l for l in plain.splitlines() if "if " in l.lower() and "then " in l.lower()]
        if lines:
            extracted_items = []
            for idx, line in enumerate(lines, 1):
                extracted_items.append({
                    "requirement_id": f"REQ-{idx:02d}",
                    "condition": line.split("then", 1)[0].replace("If", "").replace("if", "").strip(" :,."),
                    "expected_result": line.split("then", 1)[1].strip(" :.,"),
                    "source_excerpt": "Extracted from diagram",
                })
            return {
                "model": model_used,
                "requirement_count": len(extracted_items),
                "requirements": extracted_items,
                "plain_text": plain,
                "source": "diagram",
            }

        return {
            "model": model_used,
            "requirement_count": 0,
            "requirements": [],
            "plain_text": plain,
            "source": "diagram",
        }

    return {
        "model": model_used,
        "requirement_count": len(items),
        "requirements": items,
        "source": "diagram",
    }


def requirements_to_text(requirements: list[dict]) -> str:
    """Convert a list of structured requirement dicts to plain text lines."""
    lines: list[str] = []
    for req in requirements:
        cond = (req.get("condition") or "").strip()
        expected = (req.get("expected_result") or "").strip()
        if cond and expected:
            lines.append(f"If {cond}, then {expected}.")
        elif cond:
            lines.append(cond + ".")
        elif expected:
            lines.append(expected + ".")
    return "\n".join(lines)
