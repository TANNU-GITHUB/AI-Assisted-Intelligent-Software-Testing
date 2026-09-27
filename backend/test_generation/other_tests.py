"""Task 7 — Additional Test Type Generator: integration + negative tests,
converted into real pytest files, plus a persisted regression suite.
Matches the session-manifest pattern used by code_analysis/analyzer.py
and requirement_analysis/analyzer.py.

Unit tests are intentionally left out — they reuse Task 5's (white-box)
output, which doesn't exist yet. Add that branch once white_box.py lands.
"""

from __future__ import annotations

import ast
import difflib
import json
from datetime import datetime, timezone
from pathlib import Path

from config import GEMINI_API_KEY, GEMINI_MODEL
from input_handler.handler import load_session, save_session, session_dir
from input_handler.session_logging import log_session_error


class OtherTestsError(Exception):
    """Raised when Task 7 generation fails."""


def _call_llm(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise OtherTestsError("GEMINI_API_KEY not set in backend/.env")

    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(prompt)
    return response.text


def _parse_json_response(raw_text: str) -> list[dict]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise OtherTestsError(f"LLM did not return valid JSON: {exc}") from exc


def _detect_cross_function_calls(source_code: str) -> list[dict]:
    tree = ast.parse(source_code)
    defined_functions = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }

    pairs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            caller = node.name
            for inner in ast.walk(node):
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name):
                    callee = inner.func.id
                    if callee in defined_functions and callee != caller:
                        pairs.append({"caller": caller, "callee": callee})

    return [dict(t) for t in {tuple(p.items()) for p in pairs}]


def _generate_integration_tests(
    source_code: str, call_pairs: list[dict], requirement_ids: list[str]
) -> list[dict]:
    if not call_pairs:
        return []

    prompt = f"""You are generating integration test cases for the Python code below.
For each function-call pair, create ONE test case verifying the caller and
callee work correctly together (realistic input, expected output).

Function call pairs:
{json.dumps(call_pairs, indent=2)}

Valid requirement IDs (assign exactly one to every test case):
{json.dumps(requirement_ids)}

Source code:
{source_code}

Return ONLY a JSON array, no markdown, no explanation. Each item:
{{"caller": "...", "callee": "...", "input": {{...}}, "expected_output": ..., "test_type": "integration", "requirement_id": "REQ-01"}}
"""
    return _parse_json_response(_call_llm(prompt))


def _generate_negative_tests(source_code: str, requirement_ids: list[str]) -> list[dict]:
    prompt = f"""You are generating negative test cases for the Python code below.
For each function, produce test cases using invalid, missing, or malformed
inputs (wrong type, None, empty string, out-of-range values) and specify the
expected exception.

Source code:
{source_code}

Valid requirement IDs (assign exactly one to every test case):
{json.dumps(requirement_ids)}

Return ONLY a JSON array, no markdown, no explanation. Each item:
{{"function_name": "...", "input": {{...}}, "expected_exception": "ValueError", "reason": "short reason", "test_type": "negative", "requirement_id": "REQ-01"}}
"""
    return _parse_json_response(_call_llm(prompt))


def _validate_test_cases(
    cases: list[dict], requirement_ids: set[str], test_type: str
) -> None:
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            raise OtherTestsError(f"{test_type} test case {index} must be a JSON object.")
        requirement_id = str(case.get("requirement_id") or "").strip()
        if not requirement_id:
            raise OtherTestsError(
                f"{test_type} test case {index} is missing requirement_id."
            )
        if requirement_id not in requirement_ids:
            raise OtherTestsError(
                f"{test_type} test case {index} references unknown requirement_id "
                f"'{requirement_id}'."
            )


def _update_regression_suite(session_id: str, new_tests: list[dict]) -> int:
    reg_dir = session_dir(session_id) / "tests" / "regression"
    reg_dir.mkdir(parents=True, exist_ok=True)
    reg_file = reg_dir / "regression_suite.json"

    existing = json.loads(reg_file.read_text(encoding="utf-8")) if reg_file.is_file() else []
    existing.extend(new_tests)
    reg_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    return len(existing)


def _run_regression_if_source_changed(
    session_id: str, payload: dict, source_code: str
) -> dict:
    folder = session_dir(session_id)
    snapshot_path = folder / "regression" / "source_snapshot.py"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    if not snapshot_path.is_file():
        snapshot_path.write_text(source_code, encoding="utf-8")
        return payload

    previous_source = snapshot_path.read_text(encoding="utf-8")
    if previous_source == source_code:
        return payload

    source_diff = "".join(
        difflib.unified_diff(
            previous_source.splitlines(keepends=True),
            source_code.splitlines(keepends=True),
            fromfile="stored/source.py",
            tofile="updated/source.py",
        )
    )
    tests_dir = folder / "tests"
    existing_tests = list(tests_dir.rglob("test_*.py")) if tests_dir.is_dir() else []
    regression_result = {"status": "no_existing_tests", "total": 0, "tests": []}
    if existing_tests:
        try:
            from execution.analyzer import analyze_session_execution

            regression_payload = analyze_session_execution(session_id)
            regression_result = regression_payload.get("test_execution", {})
            payload = regression_payload
        except Exception as exc:
            log_session_error(session_id, "test_generation.regression", exc)
            raise OtherTestsError(
                f"Could not run the existing regression suite after source change: {exc}"
            ) from exc

    payload["regression_awareness"] = {
        "source_changed": True,
        "source_diff": source_diff,
        "execution": regression_result,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    snapshot_path.write_text(source_code, encoding="utf-8")
    return save_session(payload)


# ---------------------------------------------------------------------------
# Convert JSON test cases into real, runnable pytest files
# ---------------------------------------------------------------------------
def _write_pytest_file(session_id: str, test_type: str, cases: list[dict]) -> str:
    """
    Writes sessions/<id>/tests/<test_type>/test_<test_type>.py
    Each generated file inserts the session folder onto sys.path so it can
    do `from source import *` regardless of where pytest is invoked from.
    """
    out_dir = session_dir(session_id) / "tests" / test_type
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"test_{test_type}.py"

    lines = [
        "import sys",
        "from pathlib import Path",
        "import pytest",
        "sys.path.insert(0, str(Path(__file__).resolve().parents[2]))",
        "",
    ]
    lines.append("from source import *")
    lines.append("")
    lines.append("")

    for i, case in enumerate(cases, start=1):
        func_name = case.get("function_name") or case.get("caller") or "target"
        test_name = f"test_{test_type}_{func_name}_case{i}"
        requirement_id = case["requirement_id"]
        input_kwargs = case.get("input", {}) or {}

        lines.append(
            f"@pytest.mark.parametrize('_requirement_id', [{requirement_id!r}], "
            f"ids=[{requirement_id!r}])"
        )
        if test_type == "negative":
            expected_exc = case.get("expected_exception", "Exception")
            lines.append(f"def {test_name}(_requirement_id):")
            lines.append(f"    with pytest.raises({expected_exc}):")
            lines.append(f"        {func_name}(**{input_kwargs!r})")
        else:
            expected = case.get("expected_output")
            lines.append(f"def {test_name}(_requirement_id):")
            lines.append(f"    assert {func_name}(**{input_kwargs!r}) == {expected!r}")
        lines.append("")

    out_file.write_text("\n".join(lines), encoding="utf-8")
    return str(out_file)


# ---------------------------------------------------------------------------
# Orchestrator — mirrors analyze_session() / analyze_session_requirements()
# ---------------------------------------------------------------------------
def analyze_session_other_tests(session_id: str) -> dict:
    payload = load_session(session_id)
    folder = session_dir(session_id)

    source_path = folder / "source.py"
    if not source_path.is_file():
        raise FileNotFoundError(f"source.py not found for session '{session_id}'.")
    source_code = source_path.read_text(encoding="utf-8")
    payload = _run_regression_if_source_changed(session_id, payload, source_code)

    requirements = (payload.get("requirement_analysis") or {}).get("requirements") or []
    requirement_ids = {
        str(requirement.get("requirement_id") or "").strip()
        for requirement in requirements
        if isinstance(requirement, dict)
    }
    if not requirement_ids or "" in requirement_ids:
        raise OtherTestsError(
            "Requirement analysis with valid requirement IDs must run before test generation."
        )

    try:
        call_pairs = _detect_cross_function_calls(source_code)
        integration_tests = _generate_integration_tests(
            source_code, call_pairs, sorted(requirement_ids)
        )
        negative_tests = _generate_negative_tests(source_code, sorted(requirement_ids))
        _validate_test_cases(integration_tests, requirement_ids, "integration")
        _validate_test_cases(negative_tests, requirement_ids, "negative")
    except OtherTestsError as exc:
        log_session_error(session_id, "test_generation", exc)
        raise
    except Exception as exc:  # noqa: BLE001
        log_session_error(session_id, "test_generation", exc)
        raise OtherTestsError(str(exc)) from exc

    regression_total = _update_regression_suite(
        session_id, integration_tests + negative_tests
    )

    integration_file = _write_pytest_file(session_id, "integration", integration_tests)
    negative_file = _write_pytest_file(session_id, "negative", negative_tests)

    result = {
        "integration_tests": integration_tests,
        "negative_tests": negative_tests,
        "integration_count": len(integration_tests),
        "negative_count": len(negative_tests),
        "regression_suite_size": regression_total,
        "files_written": {
            "integration": integration_file,
            "negative": negative_file,
        },
    }

    payload["other_tests"] = result
    save_session(payload)
    return payload