"""Task 5 — White Box Test Case Generator."""

from __future__ import annotations

import ast
import json
import re
from typing import Any, Callable

from config import GEMINI_API_KEY, GEMINI_MODEL
from input_handler.handler import load_session, save_session, session_dir
from input_handler.session_logging import log_session_error
from test_generation.prompts_white_box import PROMPT_TEMPLATE, STRICT_RETRY_PROMPT


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


def _call_gemini(prompt: str, api_key: str, model_name: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise WhiteBoxError("Gemini returned an empty response.")
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
    llm_call: Callable[..., str] = _call_gemini,
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
                f"Gemini did not return valid JSON for {function_name}: {exc}"
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
    fn_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            fn_node = node
            break
    if fn_node is None:
        raise WhiteBoxError(f"Could not locate function {name} for fallback generation.")

    namespace: dict[str, Any] = {}
    exec(compile(ast.Module(body=list(tree.body), type_ignores=[]), "<module>", "exec"), namespace)
    target = namespace.get(name)
    if not callable(target):
        raise WhiteBoxError(f"Function {name} is not callable in fallback namespace.")

    def add_case(
        case_id: str,
        description: str,
        inputs: dict[str, Any],
        *,
        expected_output: Any = None,
        expected_exception: str | None = None,
    ) -> None:
        cases.append(
            {
                "case_id": case_id,
                "description": description,
                "input": inputs,
                "expected_output": expected_output,
                "expected_exception": expected_exception,
                "test_type": "white_box",
                "function_name": name,
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
        try:
            result = target(**smoke_input)
            add_case("smoke", "default smoke test", smoke_input, expected_output=result)
        except Exception as exc:
            add_case(
                "smoke",
                "default smoke test raises",
                smoke_input,
                expected_exception=type(exc).__name__,
            )
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

        try:
            result = target(**inputs)
            add_case(
                f"branch{branch_index}",
                f"covers branch at line {branch.get('lineno')}",
                inputs,
                expected_output=result,
            )
        except Exception as exc:
            add_case(
                f"branch{branch_index}",
                f"covers branch at line {branch.get('lineno')}",
                inputs,
                expected_exception=type(exc).__name__,
            )

    if bool_params and len({json.dumps(c["input"], sort_keys=True) for c in cases}) < 2:
        alt = dict(cases[0]["input"]) if cases else {p: True for p in bool_params}
        for param in bool_params:
            alt[param] = not alt.get(param, True)
        try:
            result = target(**alt)
            add_case("bool_flip", "alternate boolean branch", alt, expected_output=result)
        except Exception as exc:
            add_case(
                "bool_flip",
                "alternate boolean branch",
                alt,
                expected_exception=type(exc).__name__,
            )

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
    out_dir = session_dir(session_id) / "tests" / "white_box"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_]+", "_", function_name)
    out_file = out_dir / f"test_{safe_name}.py"

    lines = [
        "import sys",
        "from pathlib import Path",
        "import pytest",
        "",
        "sys.path.insert(0, str(Path(__file__).resolve().parents[2]))",
        "from source import *",
        "",
    ]

    for index, case in enumerate(cases, start=1):
        req_id = case["requirement_id"]
        test_name = f"test_white_box_{safe_name}_case{index}"
        inputs = case.get("input", {}) or {}
        lines.append(
            f"@pytest.mark.parametrize('_requirement_id', [{req_id!r}], ids=[{req_id!r}])"
        )
        lines.append(f"def {test_name}(_requirement_id):")
        if case.get("expected_exception"):
            lines.append(f"    with pytest.raises({case['expected_exception']}):")
            lines.append(f"        {function_name}(**{inputs!r})")
        else:
            expected = case.get("expected_output")
            lines.append(f"    assert {function_name}(**{inputs!r}) == {expected!r}")
        lines.append("")

    out_file.write_text("\n".join(lines), encoding="utf-8")
    return str(out_file)


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

    key = GEMINI_API_KEY.strip()
    model = GEMINI_MODEL
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
                if key and key != "your_gemini_api_key_here":
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
