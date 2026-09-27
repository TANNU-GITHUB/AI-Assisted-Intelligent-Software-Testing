"""Task 7 — Additional Test Type Generator: integration + negative tests,
converted into real pytest files, plus a persisted regression suite.
Matches the session-manifest pattern used by code_analysis/analyzer.py
and requirement_analysis/analyzer.py.

Unit tests are intentionally left out — they reuse Task 5's (white-box)
output, which doesn't exist yet. Add that branch once white_box.py lands.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from config import GEMINI_API_KEY, GEMINI_MODEL
from input_handler.handler import load_session, save_session, session_dir


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


def _generate_integration_tests(source_code: str, call_pairs: list[dict]) -> list[dict]:
    if not call_pairs:
        return []

    prompt = f"""You are generating integration test cases for the Python code below.
For each function-call pair, create ONE test case verifying the caller and
callee work correctly together (realistic input, expected output).

Function call pairs:
{json.dumps(call_pairs, indent=2)}

Source code:
{source_code}

Return ONLY a JSON array, no markdown, no explanation. Each item:
{{"caller": "...", "callee": "...", "input": {{...}}, "expected_output": ..., "test_type": "integration"}}
"""
    return _parse_json_response(_call_llm(prompt))


def _generate_negative_tests(source_code: str) -> list[dict]:
    prompt = f"""You are generating negative test cases for the Python code below.
For each function, produce test cases using invalid, missing, or malformed
inputs (wrong type, None, empty string, out-of-range values) and specify the
expected exception.

Source code:
{source_code}

Return ONLY a JSON array, no markdown, no explanation. Each item:
{{"function_name": "...", "input": {{...}}, "expected_exception": "ValueError", "reason": "short reason", "test_type": "negative"}}
"""
    return _parse_json_response(_call_llm(prompt))


def _update_regression_suite(session_id: str, new_tests: list[dict]) -> int:
    reg_dir = session_dir(session_id) / "tests" / "regression"
    reg_dir.mkdir(parents=True, exist_ok=True)
    reg_file = reg_dir / "regression_suite.json"

    existing = json.loads(reg_file.read_text(encoding="utf-8")) if reg_file.is_file() else []
    existing.extend(new_tests)
    reg_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    return len(existing)


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
        "sys.path.insert(0, str(Path(__file__).resolve().parents[2]))",
        "",
    ]
    if test_type == "negative":
        lines.append("import pytest")
    lines.append("from source import *")
    lines.append("")
    lines.append("")

    for i, case in enumerate(cases, start=1):
        func_name = case.get("function_name") or case.get("callee") or "target"
        test_name = f"test_{test_type}_{func_name}_case{i}"
        input_kwargs = case.get("input", {}) or {}

        if test_type == "negative":
            expected_exc = case.get("expected_exception", "Exception")
            lines.append(f"def {test_name}():")
            lines.append(f"    with pytest.raises({expected_exc}):")
            lines.append(f"        {func_name}(**{input_kwargs!r})")
        else:
            expected = case.get("expected_output")
            lines.append(f"def {test_name}():")
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

    try:
        call_pairs = _detect_cross_function_calls(source_code)
        integration_tests = _generate_integration_tests(source_code, call_pairs)
        negative_tests = _generate_negative_tests(source_code)
    except OtherTestsError:
        raise
    except Exception as exc:  # noqa: BLE001
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