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
    calls = []
    monkeypatch.setattr("test_generation.black_box.NVIDIA_API_KEY", "test-key")
    monkeypatch.setattr(
        "test_generation.black_box._generate_cases_with_llm",
        lambda **kwargs: (
            calls.append(kwargs)
            or [
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
            ]
        ),
    )
    result = analyze_session_black_box(session_id)
    assert result["black_box_tests"]["generation_source"] == "llm"
    assert result["black_box_tests"]["test_count"] == 1
    assert calls[0]["requirements_text"] == "Adding two numbers returns their sum."


@pytest.mark.parametrize(
    ("requirements_file_content", "error"),
    [
        (None, "Requirements text file not found"),
        ("  \n", "Requirements text file is empty"),
    ],
)
def test_black_box_requires_saved_requirements_text(
    tmp_path, monkeypatch, requirements_file_content, error
):
    session_id = _seed_session(tmp_path, monkeypatch)
    requirements_path = tmp_path / session_id / "requirements.txt"
    if requirements_file_content is None:
        requirements_path.unlink()
    else:
        requirements_path.write_text(requirements_file_content, encoding="utf-8")

    with pytest.raises(BlackBoxError, match=error):
        analyze_session_black_box(session_id)


def test_domain_defaults_and_english_conditions():
    from test_generation.black_box import (
        _build_ast_hints,
        _infer_domain_default,
        _inputs_from_condition,
        _pick_function_for_requirement,
    )

    # Ensure single-char 'n' doesn't corrupt family_income and 'age' doesn't corrupt message
    assert _infer_domain_default("family_income", "float") >= 1000.0
    assert _infer_domain_default("gpa", "float") <= 4.0
    assert _infer_domain_default("prices", "list[float]") == [50.0, 100.0]
    assert isinstance(_infer_domain_default("message", "str"), str)

    # English error bounds & natural language conditions
    err_score = _inputs_from_condition(
        "Scores below 0 or above 100 must raise ValueError.",
        [{"name": "score", "annotation": "float"}],
        expect_error=True,
    )
    assert err_score["score"] < 0 or err_score["score"] > 100

    neg_income = _inputs_from_condition(
        "Negative family income must raise ValueError.",
        [{"name": "family_income", "annotation": "float"}],
        expect_error=True,
    )
    assert neg_income["family_income"] < 0

    tier = _inputs_from_condition(
        "Students with GPA at least 3.8 and family income at or below 25000 receive 5000 scholarship.",
        [
            {"name": "gpa", "annotation": "float"},
            {"name": "family_income", "annotation": "float"},
        ],
    )
    assert tier["gpa"] >= 3.8
    assert tier["family_income"] <= 25000

    # Whole-word & AST function selection
    src = (
        "def validate_score(score: float) -> None:\n"
        "    if score < 0 or score > 100:\n"
        "        raise ValueError('bad')\n"
        "def calculate_gpa(scores: list[float]) -> float:\n"
        "    if not scores:\n"
        "        raise ValueError('Scores list cannot be empty')\n"
        "    return 4.0\n"
    )
    catalog = [
        {"name": "validate_score", "params": [{"name": "score", "annotation": "float"}]},
        {"name": "calculate_gpa", "params": [{"name": "scores", "annotation": "list[float]"}]},
    ]
    hints = _build_ast_hints(src)
    picked = _pick_function_for_requirement(
        {"condition": "An empty scores list must raise ValueError.", "expected_result": "ValueError"},
        catalog,
        0,
        ast_hints=hints,
    )
    assert picked == "calculate_gpa"


def test_negated_error_descriptions_and_additive_bonus_cases():
    from test_generation.black_box import (
        _fallback_cases,
        _normalize_cases,
        description_implies_exception,
    )

    assert description_implies_exception("No error raised for valid input") is None
    assert description_implies_exception("Score out of bounds raises ValueError") == "ValueError"

    normalized = _normalize_cases(
        [
            {
                "case_id": "bb1",
                "description": "No error raised when score is valid",
                "requirement_id": "REQ-01",
                "function_name": "check_score",
                "input": {"score": 80},
            }
        ],
        {"REQ-01"},
        {"check_score"},
        [{"name": "check_score", "params": [{"name": "score", "annotation": "int"}]}],
    )
    assert normalized[0]["expected_exception"] is None

    src = (
        "def determine_scholarship(gpa: float, family_income: float) -> float:\n"
        "    if gpa >= 3.5:\n"
        "        return 2000.0\n"
        "    return 0.0\n\n"
        "def evaluate_student(scores: list[float], family_income: float) -> dict:\n"
        "    gpa = round((sum(scores) / len(scores) / 100.0) * 4.0, 2)\n"
        "    grant = determine_scholarship(gpa, family_income)\n"
        "    status = \"Dean's List\" if gpa >= 3.7 else 'Good Standing'\n"
        "    return {'gpa': gpa, 'scholarship': grant, 'status': status}\n"
    )
    api = [
        {
            "name": "determine_scholarship",
            "return_type": "float",
            "params": [{"name": "gpa", "annotation": "float"}, {"name": "family_income", "annotation": "float"}],
        },
        {
            "name": "evaluate_student",
            "return_type": "dict",
            "params": [{"name": "scores", "annotation": "list[float]"}, {"name": "family_income", "annotation": "float"}],
        },
    ]
    reqs = [
        {"requirement_id": "REQ-01", "condition": "evaluate_student assigns status Dean's List when gpa >= 3.7.", "expected_result": "Dean's List"},
        {"requirement_id": "REQ-02", "condition": "evaluate_student must add a 500.0 honor bonus to scholarship when status is Dean's List.", "expected_result": "+500.0 bonus"},
    ]
    cases = _fallback_cases(reqs, api, src)
    by_req = {c["requirement_id"]: c for c in cases}
    assert by_req["REQ-01"]["expected_field"] == "status"
    assert by_req["REQ-01"]["expected_field_value"] == "Dean's List"
    assert by_req["REQ-02"]["expected_field"] == "scholarship"
    assert by_req["REQ-02"]["expected_callee"] == "determine_scholarship"
    assert by_req["REQ-02"]["expected_delta"] == 500.0


def test_nan_condition_generates_safe_nan_expression_and_catches_missing_check():
    from test_generation.black_box import _inputs_from_condition
    from test_generation.safe_codegen import json_expression

    inputs = _inputs_from_condition(
        "Scores that are NAN must raise value error.",
        [{"name": "score", "annotation": "float"}],
        expect_error=True,
    )
    assert str(inputs["score"]).lower() == "nan"
    expr = json_expression(inputs)
    assert "float('nan')" in expr
