"""Extract testable requirements from an uploaded diagram or flowchart image."""

from __future__ import annotations

from llm_client import LLMError, generate_from_image
from requirement_analysis.analyzer import _heuristic_requirements, _normalize

DIAGRAM_PROMPT = """\
You are a software test analyst. The image shows a diagram, flowchart, or UML diagram \
describing software behaviour.

Extract all discrete, testable scenarios from this diagram.

Return ONLY valid JSON (no markdown fences, no commentary):
{
  "requirements": [
    {
      "requirement_id": "REQ-01",
      "condition": "plain-language IF condition that can be checked",
      "expected_result": "plain-language THEN expected outcome",
      "source_excerpt": "brief description of which part of the diagram this came from"
    }
  ]
}

Rules:
- requirement_id must be REQ-01, REQ-02, ... in order.
- Each item must be independently testable.
- Capture every decision branch, state transition, and flow path shown.
- Do not invent behaviour not shown in the diagram.
"""


def extract_requirements_from_diagram(image_bytes: bytes, mime_type: str) -> dict:
    """Use a vision LLM to extract structured requirements from a diagram image.

    Returns a dict with keys: model, requirement_count, requirements, source.
    Falls back to heuristic extraction when no vision model is available.
    """
    from json_utils import extract_json as _extract_json  # local import to avoid circular

    try:
        raw, model_used = generate_from_image(image_bytes, mime_type, DIAGRAM_PROMPT)
        items = _normalize(_extract_json(raw))
        return {
            "model": model_used,
            "requirement_count": len(items),
            "requirements": items,
            "source": "diagram",
        }
    except LLMError as exc:
        fallback_items = _heuristic_requirements(
            "Diagram-based requirement (vision model unavailable)"
        )
        return {
            "model": "heuristic-fallback",
            "requirement_count": len(fallback_items),
            "requirements": fallback_items,
            "fallback_reason": str(exc),
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
