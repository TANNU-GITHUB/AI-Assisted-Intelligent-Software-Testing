import json
from pathlib import Path

import pytest

from code_analysis.analyzer import analyze_session
from input_handler.handler import create_session
from test_generation.white_box import WhiteBoxError, analyze_session_white_box


SAMPLE = Path("examples/sample_source.py").read_text(encoding="utf-8")
REQUIREMENTS = Path("examples/sample_requirements.txt").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def isolated_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr("input_handler.handler.SESSIONS_DIR", tmp_path)
    return tmp_path


def _session_with_analysis(tmp_path):
    payload = create_session(
        source_code=SAMPLE,
        requirements_text=REQUIREMENTS,
        original_filename="sample_source.py",
    )
    analyze_session(payload["session_id"])
    return payload["session_id"]


def test_white_box_fallback_writes_pytest_files(tmp_path):
    session_id = _session_with_analysis(tmp_path)
    result = analyze_session_white_box(session_id)

    white_box = result["white_box_tests"]
    assert white_box["test_count"] >= 2
    assert len(white_box["files_written"]) >= 2

    for file_path in white_box["files_written"]:
        assert Path(file_path).is_file()
        content = Path(file_path).read_text(encoding="utf-8")
        assert "pytest" in content
        assert "from source import *" in content


def test_white_box_requires_code_analysis(tmp_path):
    payload = create_session(
        source_code=SAMPLE,
        requirements_text=REQUIREMENTS,
        original_filename="sample_source.py",
    )
    with pytest.raises(WhiteBoxError, match="code analysis"):
        analyze_session_white_box(payload["session_id"])


def test_white_box_uses_llm_when_available(tmp_path, monkeypatch):
    session_id = _session_with_analysis(tmp_path)
    fake_cases = {
        "test_cases": [
            {
                "case_id": "case1",
                "description": "member discount",
                "input": {"price": 100.0, "is_member": True},
                "expected_output": 90.0,
                "expected_exception": None,
            }
        ]
    }

    monkeypatch.setattr(
        "test_generation.white_box.GEMINI_API_KEY",
        "test-key",
    )
    monkeypatch.setattr(
        "test_generation.white_box._generate_cases_with_llm",
        lambda **kwargs: [
            {
                **item,
                "test_type": "white_box",
                "function_name": kwargs["function_name"],
            }
            for item in json.loads(json.dumps(fake_cases["test_cases"]))
        ],
    )

    result = analyze_session_white_box(session_id)
    generated = [
        fn for fn in result["white_box_tests"]["functions"] if fn["function"] == "calculate_discount"
    ]
    assert generated
    assert generated[0]["source"] == "llm"
    assert generated[0]["case_count"] == 1
