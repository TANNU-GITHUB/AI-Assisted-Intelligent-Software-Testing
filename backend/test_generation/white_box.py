"""Task 5 — White Box Test Case Generator."""

from __future__ import annotations

import ast
import json
import re
from typing import Any, Callable

from config import NVIDIA_API_KEY, NVIDIA_MODEL
from llm_client import generate_text, llm_is_configured
from input_handler.handler import load_session, save_session, session_dir, session_locked
from input_handler.session_logging import log_session_error
from test_generation.prompts_white_box import PROMPT_TEMPLATE, STRICT_RETRY_PROMPT
from test_generation.safe_codegen import (
    expected_exception_expression,
    function_call_expression,
    generated_test_imports,
    json_expression,
    require_python_identifier,
)


class WhiteBoxError(Exception):
    """Raised when white-box test generation fails."""


def _extract_json(text: str) -> Any:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise json.JSONDecodeError("No JSON object found", cleaned, 0)
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def _call_llm(prompt: str, api_key: str, model_name: str) -> str:
    text, _model_used = generate_text(prompt, api_key=api_key, model_name=model_name)
    return text


def _function_source(module_source: str, lineno: int, end_lineno: int) -> str:
    lines = module_source.splitlines()
    start = max(lineno - 1, 0)
    end = min(end_lineno, len(lines))
    return "\n".join(lines[start:end])


def _normalize_cases(data: Any, function_name: str) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        raise WhiteBoxError("LLM JSON root must be an object.")
    items = data.get("test_cases")
    if not isinstance(items, list) or not items:
        raise WhiteBoxError(f"No test cases returned for {function_name}.")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise WhiteBoxError(f"Test case {index} for {function_name} must be an object.")
        case_id = str(item.get("case_id") or f"case{index}").strip()
        description = str(item.get("description") or case_id).strip()
        inputs = item.get("input")
        if not isinstance(inputs, dict):
            raise WhiteBoxError(f"Test case {case_id} must include an 'input' object.")
        expected_output = item.get("expected_output")
        expected_exception = item.get("expected_exception")
        if expected_exception is None and "expected_output" not in item:
            raise WhiteBoxError(
                f"Test case {case_id} needs expected_output or expected_exception."
            )
        if expected_exception:
            try:
                expected_exception = require_python_identifier(
                    str(expected_exception).strip(), "Exception name"
                )
            except ValueError as exc:
                raise WhiteBoxError(str(exc)) from exc
        normalized.append(
            {
                "case_id": case_id,
                "description": description,
                "input": inputs,
                "expected_output": expected_output,
                "expected_exception": str(expected_exception).strip()
                if expected_exception
                else None,
                "test_type": "white_box",
                "function_name": function_name,
            }
        )
    return normalized


def _generate_cases_with_llm(
    *,
    function_name: str,
    function_source: str,
    module_source: str,
    branches: list[dict[str, Any]],
    api_key: str,
    model_name: str,
    llm_call: Callable[..., str] = _call_llm,
) -> list[dict[str, Any]]:
    branch_map = json.dumps(branches, indent=2)
    prompt = PROMPT_TEMPLATE.format(
        function_name=function_name,
        branch_map=branch_map,
        function_source=function_source,
        module_source=module_source,
    )
    try:
        raw = llm_call(prompt, api_key, model_name)
        return _normalize_cases(_extract_json(raw), function_name)
    except (json.JSONDecodeError, WhiteBoxError, TypeError, ValueError):
        retry = STRICT_RETRY_PROMPT.format(
            function_name=function_name,
            branch_map=branch_map,
            function_source=function_source,
        )
        try:
            raw = llm_call(retry, api_key, model_name)
            return _normalize_cases(_extract_json(raw), function_name)
        except (json.JSONDecodeError, WhiteBoxError, TypeError, ValueError) as exc:
            raise WhiteBoxError(
                f"LLM did not return valid JSON for {function_name}: {exc}"
            ) from exc


def _fallback_cases(
    function_meta: dict[str, Any],
    module_source: str,
) -> list[dict[str, Any]]:
    """Deterministic branch-oriented cases when the LLM is unavailable or invalid."""
    name = function_meta["name"]
    if "." in function_meta.get("qualified_name", name):
        raise WhiteBoxError(
            f"Fallback generator does not support methods yet: {function_meta['qualified_name']}"
        )

    param_names = [p["name"] for p in function_meta.get("params", [])]
    branches = function_meta.get("branches") or []
    cases: list[dict[str, Any]] = []

    tree = ast.parse(module_source)
    if not any(
        isinstance(node, ast.FunctionDef) and node.name == name
        for node in ast.walk(tree)
    ):
        raise WhiteBoxError(f"Could not locate function {name} for fallback generation.")

    def add_case(
        case_id: str,
        description: str,
        inputs: dict[str, Any],
    ) -> None:
        cases.append(
            {
                "case_id": case_id,
                "description": description,
                "input": inputs,
                "expected_output": None,
                "expected_exception": None,
                "test_type": "white_box",
                "function_name": name,
                "assert_output": False,
            }
        )

    if not branches:
        smoke_input = {}
        for param in function_meta.get("params", []):
            annotation = (param.get("annotation") or "").lower()
            default = param.get("default")
            if default is not None:
                smoke_input[param["name"]] = ast.literal_eval(default)
            elif "bool" in annotation:
                smoke_input[param["name"]] = False
            elif "list" in annotation:
                smoke_input[param["name"]] = []
            elif "int" in annotation:
                smoke_input[param["name"]] = 0
            elif "float" in annotation:
                smoke_input[param["name"]] = 0.0
            else:
                smoke_input[param["name"]] = 0
        add_case("smoke", "default smoke test", smoke_input)
        return cases

    bool_params = [p for p in param_names if p.startswith("is_") or p.endswith("_flag")]
    numeric_params = [
        p
        for p in param_names
        if p not in bool_params and p not in {"prices", "items", "values"}
    ]

    for branch_index, branch in enumerate(branches, start=1):
        condition = (branch.get("condition") or "").lower()
        inputs: dict[str, Any] = {}
        for param in param_names:
            if param in bool_params:
                inputs[param] = True
            elif param == "prices":
                inputs[param] = [100.0, 50.0]
            elif param in numeric_params:
                inputs[param] = 100.0
            else:
                inputs[param] = []

        if "< 0" in condition or "<0" in condition:
            for param in numeric_params:
                inputs[param] = -1.0
        if "not " in condition and bool_params:
            inputs[bool_params[0]] = False
        elif bool_params and any(token in condition for token in bool_params):
            for param in bool_params:
                inputs[param] = param in condition and "not " not in condition

        add_case(
            f"branch{branch_index}",
            f"covers branch at line {branch.get('lineno')}",
            inputs,
        )

    if bool_params and len({json.dumps(c["input"], sort_keys=True) for c in cases}) < 2:
        alt = dict(cases[0]["input"]) if cases else {p: True for p in bool_params}
        for param in bool_params:
            alt[param] = not alt.get(param, True)
        add_case("bool_flip", "alternate boolean branch", alt)

    if not cases:
        raise WhiteBoxError(f"Fallback generator produced no cases for {name}.")
    return cases


def _assign_requirement_ids(
    cases: list[dict[str, Any]], requirement_ids: list[str]
) -> list[dict[str, Any]]:
    if not requirement_ids:
        requirement_ids = ["REQ-01"]
    for index, case in enumerate(cases):
        case["requirement_id"] = requirement_ids[index % len(requirement_ids)]
    return cases


def _write_pytest_file(
    session_id: str,
    function_name: str,
    cases: list[dict[str, Any]],
) -> str:
    try:
        function_name = require_python_identifier(function_name, "Function name")
    except ValueError as exc:
        raise WhiteBoxError(str(exc)) from exc
    out_dir = session_dir(session_id) / "tests" / "white_box"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_]+", "_", function_name)
    out_file = out_dir / f"test_{safe_name}.py"

    lines = [
        "import sys",
        "from pathlib import Path",
        "",
        "sys.path.insert(0, str(Path(__file__).resolve().parents[2]))",
        "",
    ]
    lines.extend(generated_test_imports())

    for index, case in enumerate(cases, start=1):
        req_id = case["requirement_id"]
        test_name = f"test_white_box_{safe_name}_case{index}"
        inputs = case.get("input", {}) or {}
        lines.append(
            f"@pytest.mark.parametrize('_requirement_id', [{req_id!r}], ids=[{req_id!r}])"
        )
        lines.append(f"def {test_name}(_requirement_id):")
        if not case.get("assert_output", True):
            lines.append(
                '    pytest.skip("Static fallback cannot determine the expected output.")'
            )
        elif case.get("expected_exception"):
            exception_name = expected_exception_expression(case["expected_exception"])
            call = function_call_expression(function_name, inputs)
            lines.append(f"    with pytest.raises({exception_name}):")
            lines.append(f"        {call}")
        else:
            expected = case.get("expected_output")
            call = function_call_expression(function_name, inputs)
            lines.append(f"    assert {call} == {json_expression(expected)}")
        lines.append("")

    content = "\n".join(lines)
    tmp = out_file.with_suffix(out_file.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(out_file)
    return str(out_file)


@session_locked
def analyze_session_white_box(session_id: str) -> dict:
    payload = load_session(session_id)
    folder = session_dir(session_id)
    source_path = folder / "source.py"
    if not source_path.is_file():
        raise FileNotFoundError(f"source.py not found for session '{session_id}'.")

    code_analysis = payload.get("code_analysis") or {}
    functions = code_analysis.get("functions") or []
    if not functions:
        raise WhiteBoxError("Run code analysis (Task 3) before white-box test generation.")

    requirements = (payload.get("requirement_analysis") or {}).get("requirements") or []
    requirement_ids = [
        str(item.get("requirement_id") or "").strip()
        for item in requirements
        if isinstance(item, dict) and item.get("requirement_id")
    ]

    module_source = source_path.read_text(encoding="utf-8")

    all_cases: list[dict[str, Any]] = []
    files_written: list[str] = []
    per_function: list[dict[str, Any]] = []

    key = NVIDIA_API_KEY.strip()
    model = NVIDIA_MODEL
    llm_available = llm_is_configured()
    try:
        for fn in functions:
            if fn.get("is_async"):
                continue
            qualified = fn.get("qualified_name") or fn["name"]
            if "." in qualified:
                per_function.append(
                    {
                        "function": qualified,
                        "status": "skipped",
                        "reason": "Class methods are not generated yet.",
                        "case_count": 0,
                    }
                )
                continue

            name = fn["name"]
            snippet = _function_source(module_source, fn["lineno"], fn["end_lineno"])
            branches = fn.get("branches") or []
            source = "fallback"
            try:
                if llm_available:
                    cases = _generate_cases_with_llm(
                        function_name=name,
                        function_source=snippet,
                        module_source=module_source,
                        branches=branches,
                        api_key=key,
                        model_name=model,
                    )
                    source = "llm"
                else:
                    cases = _fallback_cases(fn, module_source)
            except Exception:
                llm_available = False
                cases = _fallback_cases(fn, module_source)
                source = "fallback"

            cases = _assign_requirement_ids(cases, requirement_ids)
            all_cases.extend(cases)
            file_path = _write_pytest_file(session_id, name, cases)
            files_written.append(file_path)
            per_function.append(
                {
                    "function": qualified,
                    "status": "generated",
                    "source": source,
                    "case_count": len(cases),
                    "cases": cases,
                    "file": file_path,
                }
            )

    except WhiteBoxError as exc:
        log_session_error(session_id, "white_box", exc)
        raise
    except Exception as exc:  # noqa: BLE001
        log_session_error(session_id, "white_box", exc)
        raise WhiteBoxError(str(exc)) from exc

    result = {
        "test_count": len(all_cases),
        "function_count": len(per_function),
        "files_written": files_written,
        "functions": per_function,
        "test_cases": all_cases,
    }
    payload["white_box_tests"] = result
    payload["status"] = "white_box_generated"
    save_session(payload)
    return payload
