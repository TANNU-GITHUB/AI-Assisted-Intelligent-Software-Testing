import pytest

from llm_client import LLMError
from requirement_analysis.diagram_extractor import (
    DiagramExtractionError,
    extract_requirements_from_diagram,
)


def test_extracts_structured_requirements_from_vision_response(monkeypatch):
    monkeypatch.setattr(
        "requirement_analysis.diagram_extractor.generate_from_image",
        lambda *_args, **_kwargs: (
            '{"requirements":[{"condition":"payment succeeds",'
            '"expected_result":"order is confirmed"}]}',
            "nvidia:test-vision",
        ),
    )

    result = extract_requirements_from_diagram(b"image", "image/png")

    assert result["model"] == "nvidia:test-vision"
    assert result["requirement_count"] == 1
    assert result["requirements"][0]["requirement_id"] == "REQ-01"
    assert result["requirements"][0]["condition"] == "payment succeeds"


def test_preserves_non_json_vision_transcription_as_plain_text(monkeypatch):
    monkeypatch.setattr(
        "requirement_analysis.diagram_extractor.generate_from_image",
        lambda *_args, **_kwargs: ("If paid, then ship the order.", "nvidia:test-vision"),
    )

    result = extract_requirements_from_diagram(b"image", "image/png")

    assert result["plain_text"] == "If paid, then ship the order."
    assert result["requirements"] == []


def test_vision_failure_is_reported_without_placeholder_requirements(monkeypatch):
    def _fail(*_args, **_kwargs):
        raise LLMError("endpoint unavailable")

    monkeypatch.setattr(
        "requirement_analysis.diagram_extractor.generate_from_image", _fail
    )

    with pytest.raises(DiagramExtractionError, match="Could not analyze the image") as exc:
        extract_requirements_from_diagram(b"image", "image/png")
    assert "endpoint unavailable" in str(exc.value)
    assert "NVIDIA" in str(exc.value)


def test_invalid_structured_vision_output_is_reported(monkeypatch):
    monkeypatch.setattr(
        "requirement_analysis.diagram_extractor.generate_from_image",
        lambda *_args, **_kwargs: ('{"requirements":[]}', "nvidia:test-vision"),
    )

    with pytest.raises(DiagramExtractionError, match="did not return usable requirements"):
        extract_requirements_from_diagram(b"image", "image/png")


def test_extracts_from_alternative_keys_or_fallback(monkeypatch):
    # Tests alternative key like scenarios
    monkeypatch.setattr(
        "requirement_analysis.diagram_extractor.generate_from_image",
        lambda *_args, **_kwargs: (
            '{"scenarios":[{"condition":"member is true","expected_result":"discount 10%"}]}',
            "nvidia:test-vision",
        ),
    )
    result = extract_requirements_from_diagram(b"image", "image/png")
    assert result["requirement_count"] == 1
    assert result["requirements"][0]["condition"] == "member is true"

    # Tests fallback to plain text when requirements key is absent
    monkeypatch.setattr(
        "requirement_analysis.diagram_extractor.generate_from_image",
        lambda *_args, **_kwargs: (
            '{"title":"Login Flow","summary":"If credentials valid, then access granted."}',
            "nvidia:test-vision",
        ),
    )
    res2 = extract_requirements_from_diagram(b"image", "image/png")
    assert "access granted" in res2["plain_text"]
