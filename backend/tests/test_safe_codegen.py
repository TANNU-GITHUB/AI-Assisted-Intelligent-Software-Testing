import ast
from pathlib import Path

import pytest

from test_generation.black_box import (
    BlackBoxError,
    _normalize_cases as normalize_black_box_cases,
    _write_pytest_file as write_black_box,
)
from test_generation.other_tests import (
    OtherTestsError,
    _validate_test_cases,
    _write_pytest_file as write_other_tests,
)
from test_generation.safe_codegen import (
    expected_exception_expression,
    function_call_expression,
)
from test_generation.white_box import (
    WhiteBoxError,
    _normalize_cases as normalize_white_box_cases,
    _write_pytest_file as write_white_box,
)


INJECTION = "'); __import__('os').system('echo injected'); #"


def _assert_no_injected_calls(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "system"
    ]
    assert not calls


def test_python_expressions_keep_untrusted_values_as_data():
    call = function_call_expression("target", {"value": INJECTION})

    assert "getattr(_source, 'target')" in call
    assert "__import__('os').system" not in call
    ast.parse(f"result = {call}")


@pytest.mark.parametrize(
    "exception_name",
    [INJECTION, "ValueError\nimport os", "builtins.ValueError"],
)
def test_exception_names_must_be_single_python_identifiers(exception_name):
    with pytest.raises(ValueError, match="Exception name"):
        expected_exception_expression(exception_name)


def test_exception_expression_uses_safe_name_lookup():
    expression = expected_exception_expression("ValueError")

    assert expression == "_resolve_exception('ValueError')"
    ast.parse(f"with pytest.raises({expression}):\n    pass")


def test_white_box_normalization_rejects_malicious_exception_name():
    with pytest.raises(WhiteBoxError, match="Exception name"):
        normalize_white_box_cases(
            {
                "test_cases": [
                    {
                        "input": {},
                        "expected_exception": INJECTION,
                    }
                ]
            },
            "target",
        )


def test_black_box_normalization_rejects_malicious_exception_name():
    with pytest.raises(BlackBoxError, match="Exception name"):
        normalize_black_box_cases(
            {
                "test_cases": [
                    {
                        "requirement_id": "REQ-01",
                        "function_name": "target",
                        "input": {},
                        "expected_exception": INJECTION,
                    }
                ]
            },
            {"REQ-01"},
            {"target"},
        )


def test_black_box_normalization_rejects_untrusted_function_names():
    with pytest.raises(BlackBoxError, match="unknown function"):
        normalize_black_box_cases(
            {
                "test_cases": [
                    {
                        "requirement_id": "REQ-01",
                        "function_name": INJECTION,
                        "input": {},
                        "expected_output": None,
                    }
                ]
            },
            {"REQ-01"},
            {"target"},
        )


def test_other_test_validation_rejects_untrusted_function_and_exception():
    with pytest.raises(OtherTestsError, match="valid Python identifier"):
        _validate_test_cases(
            [
                {
                    "caller": INJECTION,
                    "callee": "target",
                    "requirement_id": "REQ-01",
                }
            ],
            {"REQ-01"},
            "integration",
            {"target"},
        )

    with pytest.raises(OtherTestsError, match="Exception name"):
        _validate_test_cases(
            [
                {
                    "function_name": "target",
                    "requirement_id": "REQ-01",
                    "expected_exception": INJECTION,
                }
            ],
            {"REQ-01"},
            "negative",
            {"target"},
        )


@pytest.mark.parametrize("writer", ["white_box", "black_box", "other_tests"])
def test_generated_tests_embed_outputs_as_data(tmp_path, monkeypatch, writer):
    payload = {
        "function_name": "target",
        "caller": "target",
        "input": {"value": INJECTION},
        "expected_output": INJECTION,
        "requirement_id": "REQ-01",
    }
    if writer == "white_box":
        monkeypatch.setattr("test_generation.white_box.session_dir", lambda _sid: tmp_path)
        path = write_white_box("session", "target", [payload])
    elif writer == "black_box":
        monkeypatch.setattr("test_generation.black_box.session_dir", lambda _sid: tmp_path)
        path = write_black_box("session", [payload])
    else:
        monkeypatch.setattr("test_generation.other_tests.session_dir", lambda _sid: tmp_path)
        path = write_other_tests("session", "integration", [payload])

    _assert_no_injected_calls(Path(path))


def test_writers_reject_malicious_target_and_exception_names(tmp_path, monkeypatch):
    monkeypatch.setattr("test_generation.white_box.session_dir", lambda _sid: tmp_path)
    with pytest.raises(WhiteBoxError, match="Function name"):
        write_white_box("session", INJECTION, [])

    monkeypatch.setattr("test_generation.black_box.session_dir", lambda _sid: tmp_path)
    with pytest.raises(BlackBoxError, match="Function name"):
        write_black_box(
            "session",
            [{"function_name": INJECTION, "requirement_id": "REQ-01", "input": {}}],
        )

    monkeypatch.setattr("test_generation.other_tests.session_dir", lambda _sid: tmp_path)
    with pytest.raises(OtherTestsError, match="Function name"):
        write_other_tests(
            "session",
            "negative",
            [{"function_name": INJECTION, "requirement_id": "REQ-01"}],
        )
