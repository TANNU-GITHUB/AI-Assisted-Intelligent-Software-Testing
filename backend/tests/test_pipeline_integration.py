"""End-to-end backend pipeline: Tasks 2–5 + execution + coverage (LLM mocked)."""

import json
from pathlib import Path

import pytest

from code_analysis.analyzer import analyze_session
from execution.analyzer import analyze_session_coverage, analyze_session_execution
from input_handler.handler import create_session
from requirement_analysis.analyzer import analyze_session_requirements
from test_generation.white_box import analyze_session_white_box


SAMPLE = Path("examples/sample_source.py").read_text(encoding="utf-8")
REQUIREMENTS = Path("examples/sample_requirements.txt").read_text(encoding="utf-8")

FAKE_REQUIREMENTS = {
    "model": "test",
    "requirement_count": 2,
    "requirements": [
        {
            "requirement_id": "REQ-01",
            "condition": "is_member is True",
            "expected_result": "discount applies",
            "source_excerpt": "Members receive a discount",
        },
        {
            "requirement_id": "REQ-02",
            "condition": "price is negative",
            "expected_result": "error is raised",
            "source_excerpt": "Negative prices must be rejected",
        },
    ],
}


@pytest.fixture(autouse=True)
def isolated_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr("input_handler.handler.SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(
        "requirement_analysis.analyzer.analyze_requirements",
        lambda text, **kwargs: json.loads(json.dumps(FAKE_REQUIREMENTS)),
    )
    monkeypatch.setattr("test_generation.white_box.GEMINI_API_KEY", "")
    return tmp_path


def test_full_pipeline_through_coverage(tmp_path):
    payload = create_session(
        source_code=SAMPLE,
        requirements_text=REQUIREMENTS,
        original_filename="sample_source.py",
    )
    session_id = payload["session_id"]

    analyze_session(session_id)
    analyze_session_requirements(session_id)
    payload = analyze_session_white_box(session_id)
    assert payload["white_box_tests"]["test_count"] >= 2
    assert (tmp_path / session_id / "tests" / "white_box").is_dir()

    executed = analyze_session_execution(session_id)
    execution = executed.get("test_execution") or {}
    assert execution.get("total", 0) >= 1

    covered = analyze_session_coverage(session_id)
    coverage = covered.get("coverage") or {}
    assert coverage.get("overall_line_coverage_percent") is not None
