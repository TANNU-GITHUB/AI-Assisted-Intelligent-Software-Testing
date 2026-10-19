import pytest

from input_handler.handler import create_session, save_session
from requirement_analysis.analyzer import analyze_session_requirements
from test_generation.black_box import BlackBoxError, analyze_session_black_box
from code_analysis.analyzer import analyze_session


def _seed_session(tmp_path, monkeypatch):
    monkeypatch.setattr("input_handler.handler.SESSIONS_DIR", tmp_path)
    payload = create_session(
        source_code="def add(a, b):\n    return a + b\n",
        requirements_text="Adding two numbers returns their sum.",
    )
    session_id = payload["session_id"]
    analyze_session(session_id)
    analyze_session_requirements(session_id)
    return session_id


def test_black_box_writes_pytest_files(tmp_path, monkeypatch):
    session_id = _seed_session(tmp_path, monkeypatch)
    result = analyze_session_black_box(session_id)
    black_box = result["black_box_tests"]
    assert black_box["test_count"] >= 1
    assert black_box["files_written"]
    assert (tmp_path / session_id / "tests" / "black_box" / "test_black_box.py").is_file()


def test_black_box_requires_requirement_analysis(tmp_path, monkeypatch):
    monkeypatch.setattr("input_handler.handler.SESSIONS_DIR", tmp_path)
    payload = create_session(
        source_code="def f():\n    return 1\n",
        requirements_text="f returns one.",
    )
    with pytest.raises(BlackBoxError, match="requirement analysis"):
        analyze_session_black_box(payload["session_id"])


def test_black_box_llm_path_when_configured(tmp_path, monkeypatch):
    session_id = _seed_session(tmp_path, monkeypatch)
    monkeypatch.setattr("test_generation.black_box.NVIDIA_API_KEY", "test-key")
    monkeypatch.setattr(
        "test_generation.black_box._generate_cases_with_llm",
        lambda **kwargs: [
            {
                "case_id": "bb1",
                "description": "sum",
                "requirement_id": "REQ-01",
                "function_name": "add",
                "input": {"a": 2, "b": 3},
                "expected_output": 5,
                "expected_exception": None,
                "test_type": "black_box",
            }
        ],
    )
    result = analyze_session_black_box(session_id)
    assert result["black_box_tests"]["generation_source"] == "llm"
    assert result["black_box_tests"]["test_count"] == 1
