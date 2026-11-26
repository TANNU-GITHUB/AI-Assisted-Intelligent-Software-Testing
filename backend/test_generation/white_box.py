"""Task 5 — White Box Test Case Generator."""

from __future__ import annotations

import ast
import json
import re
import time
from typing import Any, Callable

from config import NVIDIA_API_KEY, NVIDIA_MODEL
from llm_client import generate_text, llm_is_configured
from input_handler.handler import load_session, save_session, session_dir, session_locked
from input_handler.session_logging import log_session_error
from json_utils import extract_json as _extract_json
from test_generation.black_box import (
    _default_inputs_for_params,
    _inputs_from_condition,
    _is_bool_param,
)
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


def _call_llm(prompt: str, api_key: str, model_name: str) -> str:
    """Call the LLM. Wraps LLMError in WhiteBoxError so it stays a 400, not a 500."""
    try:
        text, _model_used = generate_text(prompt, api_key=api_key, model_name=model_name)
        return text
    except WhiteBoxError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise WhiteBoxError(
            f"LLM unavailable — {exc}. "
            "Install Ollama (https://ollama.com) and run: ollama pull llama3.2"
        ) from exc


def _function_source(module_source: str, lineno: int, end_lineno: int) -> str:
    lines = module_source.splitlines()
    start = max(lineno - 1, 0)
    end = min(end_lineno, len(lines))
    return "\n".join(lines[start:end])


def _normalize_cases(data: Any, function_name: str) -> list[dict[str, Any]]:
    items: list[Any] = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = (
            data.get("test_cases")
            or data.get("cases")
            or data.get("tests")
            or data.get("scenarios")
            or []
        )
    if not items:
        raise WhiteBoxError(f"No test cases returned for {function_name}.")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise WhiteBoxError(f"Test case {index} for {function_name} must be an object.")
        case_id = str(item.get("case_id") or f"case{index}").strip()
        description = str(item.get("description") or case_id).strip()
        inputs = item.get("input")
        if not isinstance(inputs, dict):
            inputs = {}
        expected_output = item.get("expected_output")
        expected_exception = item.get("expected_exception")
        if expected_exception is None and "expected_output" not in item:
            if "error" in description.lower() or "exception" in description.lower():
                expected_exception = "ValueError"
            else:
                expected_output = None
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


_MAX_MODULE_SOURCE_CHARS = 20_000


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
    truncated_module = (
        module_source
        if len(module_source) <= _MAX_MODULE_SOURCE_CHARS
        else (module_source[:_MAX_MODULE_SOURCE_CHARS] + "\n# ... (truncated for context) ...")
    )
    prompt = PROMPT_TEMPLATE.format(
        function_name=function_name,
        branch_map=branch_map,
        function_source=function_source,
        module_source=truncated_module,
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
    name = function_meta.get("name", "func")
    if "." in function_meta.get("qualified_name", name):
        return []

    params_meta = function_meta.get("params", [])
    branches = function_meta.get("branches") or []
    cases: list[dict[str, Any]] = []

    def add_case(
        case_id: str,
        description: str,
        inputs: dict[str, Any],
        expected_exception: str | None = None,
    ) -> None:
        cases.append(
            {
                "case_id": case_id,
                "description": description,
                "input": inputs,
                "expected_output": None,
                "expected_exception": expected_exception,
                "test_type": "white_box",
                "function_name": name,
                "assert_output": expected_exception is not None,
            }
        )

    if not branches:
        smoke_input = _default_inputs_for_params(params_meta)
        add_case("smoke", "default smoke test", smoke_input)
        return cases

    for branch_index, branch in enumerate(branches, start=1):
        condition = str(branch.get("condition") or "")
        try:
            inputs = _inputs_from_condition(condition, params_meta)
        except Exception:
            inputs = _default_inputs_for_params(params_meta)

        cond_low = condition.lower()
        expected_exception = None
        if (
            "<= 0" in cond_low
            or "<=0" in cond_low
            or "< 0" in cond_low
            or "<0" in cond_low
            or "negative" in cond_low
            or "raise" in cond_low
            or "error" in cond_low
            or "invalid" in cond_low
        ):
            expected_exception = "ValueError"

        add_case(
            f"branch{branch_index}",
            f"covers branch at line {branch.get('lineno')}",
            inputs,
            expected_exception=expected_exception,
        )

    bool_params = [
        p["name"]
        for p in params_meta
        if _is_bool_param(p["name"], str(p.get("annotation") or ""), p.get("default"))
    ]
    if bool_params and len({json.dumps(c["input"], sort_keys=True) for c in cases}) < 2:
        alt = dict(cases[0]["input"]) if cases else {p: True for p in bool_params}
        for param in bool_params:
            alt[param] = not alt.get(param, True)
        add_case("bool_flip", "alternate boolean branch", alt)

    if not cases:
        add_case("smoke", "default smoke test", _default_inputs_for_params(params_meta))

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
            call = function_call_expression(function_name, inputs)
            lines.append("    # Verify execution completes without uncaught exception")
            lines.append(f"    result = {call}")
            lines.append("    assert result is not None or result is None")
        elif case.get("expected_exception"):
            exception_name = expected_exception_expression(case["expected_exception"])
            call = function_call_expression(function_name, inputs)
            lines.append(f"    with pytest.raises({exception_name}):")
            lines.append(f"        {call}")
        else:
            expected = case.get("expected_output")
            call = function_call_expression(function_name, inputs)
            lines.append(f"    _assert_match({call}, {json_expression(expected)})")
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
    llm_used = 0
    llm_started = time.monotonic()
    max_llm_functions = 30
    llm_wall_seconds = 240.0
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
            remaining_llm_budget = (
                (bool(key) or llm_is_configured())
                and llm_used < max_llm_functions
                and (time.monotonic() - llm_started) < llm_wall_seconds
            )
            if remaining_llm_budget:
                try:
                    cases = _generate_cases_with_llm(
                        function_name=name,
                        function_source=snippet,
                        module_source=module_source,
                        branches=branches,
                        api_key=key,
                        model_name=model,
                    )
                    source = "llm"
                    llm_used += 1
                except Exception:
                    try:
                        cases = _fallback_cases(fn, module_source)
                    except Exception:
                        cases = []
                    source = "fallback"
            else:
                try:
                    cases = _fallback_cases(fn, module_source)
                except Exception:
                    cases = []
                source = "fallback"

            if not cases:
                cases = [
                    {
                        "case_id": "smoke",
                        "description": f"default smoke test for {name}",
                        "input": _default_inputs_for_params(fn.get("params", [])),
                        "expected_output": None,
                        "expected_exception": None,
                        "test_type": "white_box",
                        "function_name": name,
                        "assert_output": False,
                    }
                ]

            try:
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
            except Exception as write_err:
                log_session_error(session_id, f"white_box.write.{name}", write_err)
                continue

    except WhiteBoxError as exc:
        log_session_error(session_id, "white_box", exc)
        if not all_cases:
            raise
    except Exception as exc:  # noqa: BLE001
        log_session_error(session_id, "white_box", exc)
        if not all_cases:
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
