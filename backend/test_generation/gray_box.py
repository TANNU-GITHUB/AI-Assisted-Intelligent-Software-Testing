"""Task 7 - Gray Box Test Case Generator."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from config import NVIDIA_API_KEY, NVIDIA_MODEL
from llm_client import generate_text, llm_is_configured
from input_handler.handler import load_session, save_session, session_dir, session_locked
from input_handler.session_logging import log_session_error
from json_utils import extract_json
from test_generation.black_box import (
    _fallback_cases as _black_box_fallback,
    _public_api_catalog,
    description_implies_exception,
    match_requirement_id,
    sanitize_inputs_for_params,
)
from test_generation.prompts_gray_box import PROMPT_TEMPLATE
from test_generation.safe_codegen import (
    case_assertion_lines,
    function_call_expression,
    generated_test_imports,
    require_python_identifier,
)
from test_generation.white_box import _fallback_cases as _white_box_fallback


class GrayBoxError(Exception):
    """Raised when gray-box test generation fails."""


def _call_llm(prompt: str, api_key: str, model_name: str) -> str:
    try:
        text, _model_used = generate_text(prompt, api_key=api_key, model_name=model_name)
        return text
    except Exception as exc:  # noqa: BLE001
        raise GrayBoxError(
            f"LLM unavailable - {exc}. Install Ollama and run: ollama pull llama3.2"
        ) from exc


def _normalize_cases(
    data: Any,
    requirement_ids: set[str],
    allowed_functions: set[str],
    public_api: list[dict[str, Any]] | None = None,
    structured_requirements: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    func_param_map = {
        entry["name"]: entry.get("params") or []
        for entry in (public_api or [])
    }
    items = data if isinstance(data, list) else (
        data.get("test_cases") or data.get("cases") or data.get("scenarios") or []
        if isinstance(data, dict)
        else []
    )
    if not isinstance(items, list):
        items = []

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue

        function_name = str(item.get("function_name") or "").strip()
        if function_name not in allowed_functions:
            for fn in allowed_functions:
                if fn.lower() == function_name.lower():
                    function_name = fn
                    break
            else:
                if allowed_functions:
                    function_name = sorted(allowed_functions)[index % len(allowed_functions)]
                else:
                    continue

        inputs = item.get("input")
        if not isinstance(inputs, dict):
            inputs = {}
        inputs = sanitize_inputs_for_params(inputs, func_param_map.get(function_name, []))

        desc = str(item.get("description") or f"Gray-box case {index}").strip()
        expected_output = item.get("expected_output")
        expected_exception = item.get("expected_exception")
        if expected_exception is None and "expected_output" not in item:
            expected_exception = description_implies_exception(desc)
        if expected_exception:
            try:
                require_python_identifier(str(expected_exception), "Exception name")
            except ValueError:
                expected_exception = "ValueError"

        req_id = str(item.get("requirement_id") or "").strip()
        if req_id not in requirement_ids:
            if structured_requirements:
                req_id = match_requirement_id(
                    function_name,
                    desc,
                    str(expected_exception).strip() if expected_exception else None,
                    structured_requirements,
                )
            else:
                req_id = sorted(requirement_ids)[index % len(requirement_ids)] if requirement_ids else "REQ-01"

        entry_out: dict[str, Any] = {
            "case_id": str(item.get("case_id") or f"gray{index}").strip(),
            "description": desc,
            "requirement_id": req_id,
            "function_name": function_name,
            "input": inputs,
            "expected_output": expected_output,
            "expected_exception": str(expected_exception).strip() if expected_exception else None,
            "target_branch": str(item.get("target_branch") or "").strip(),
            "test_type": "gray_box",
        }
        for extra_k in ("expected_field", "expected_field_value", "expected_callee", "expected_callee_args", "expected_delta", "assert_output"):
            if extra_k in item:
                entry_out[extra_k] = item[extra_k]
        normalized.append(entry_out)
    return normalized


def _generate_cases_with_llm(
    *,
    structured_requirements: list[dict[str, str]],
    public_api: list[dict[str, Any]],
    functions: list[dict[str, Any]],
    source_code: str,
    api_key: str,
    model_name: str,
    llm_call: Callable[..., str] = _call_llm,
) -> list[dict[str, Any]]:
    requirement_ids = {r["requirement_id"] for r in structured_requirements}
    allowed_functions = {entry["name"] for entry in public_api}
    prompt = PROMPT_TEMPLATE.format(
        structured_requirements=json.dumps(structured_requirements[:25], indent=2),
        public_api=json.dumps(public_api[:25], indent=2),
        branch_map=json.dumps([
            {
                "function": fn["name"],
                "branches": fn.get("branches") or [],
                "cyclomatic_complexity": fn.get("cyclomatic_complexity"),
            }
            for fn in functions[:20]
        ], indent=2),
        source_context=source_code[:6_000],
    )
    raw = llm_call(prompt, api_key, model_name)
    return _normalize_cases(
        extract_json(raw),
        requirement_ids,
        allowed_functions,
        public_api,
        structured_requirements=structured_requirements,
    )


def _fallback_cases(
    structured_requirements: list[dict[str, str]],
    public_api: list[dict[str, Any]],
    functions: list[dict[str, Any]],
    source_code: str,
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()

    try:
        black_cases = _black_box_fallback(structured_requirements, public_api, source_code)
    except Exception:
        black_cases = []

    for case in black_cases:
        case = dict(case)
        case["test_type"] = "gray_box"
        case["target_branch"] = "requirement behavior"
        signature = json.dumps({
            "function": case.get("function_name"),
            "input": case.get("input"),
            "expected_exception": case.get("expected_exception"),
            "expected_field": case.get("expected_field"),
        }, sort_keys=True)
        if signature not in seen:
            seen.add(signature)
            cases.append(case)

    for fn in functions:
        if fn.get("is_async") or "." in str(fn.get("qualified_name") or ""):
            continue
        try:
            branch_cases = _white_box_fallback(fn, source_code)
        except Exception:
            continue
        for index, case in enumerate(branch_cases, start=1):
            case = dict(case)
            branch = case.get("description") or f"branch {index}"
            req_id = match_requirement_id(
                case.get("function_name", fn.get("name", "")),
                branch,
                case.get("expected_exception"),
                structured_requirements,
            )
            case["test_type"] = "gray_box"
            case["requirement_id"] = req_id
            case["target_branch"] = branch
            signature = json.dumps({
                "function": case.get("function_name"),
                "input": case.get("input"),
                "expected_exception": case.get("expected_exception"),
                "expected_field": case.get("expected_field"),
            }, sort_keys=True)
            if signature not in seen:
                seen.add(signature)
                cases.append(case)

    return cases


def _write_pytest_file(session_id: str, cases: list[dict[str, Any]]) -> str:
    out_dir = session_dir(session_id) / "tests" / "gray_box"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "test_gray_box.py"

    lines = [
        "import sys",
        "from pathlib import Path",
        "",
        "sys.path.insert(0, str(Path(__file__).resolve().parents[2]))",
        "",
    ]
    lines.extend(generated_test_imports())

    for index, case in enumerate(cases, start=1):
        req_id = str(case.get("requirement_id") or "REQ-01")
        try:
            function_name = require_python_identifier(
                str(case.get("function_name") or ""), "Function name"
            )
        except ValueError as exc:
            raise GrayBoxError(str(exc)) from exc

        test_name = f"test_gray_box_case{index}_{re.sub(r'[^a-zA-Z0-9_]+', '_', req_id)}"
        inputs = case.get("input") or {}
        call = function_call_expression(function_name, inputs)
        lines.append(
            f"@pytest.mark.parametrize('_requirement_id', [{req_id!r}], ids=[{req_id!r}])"
        )
        lines.append(f"def {test_name}(_requirement_id):")
        lines.extend(case_assertion_lines(case, call))
        lines.append("")

    tmp = out_file.with_suffix(out_file.suffix + ".tmp")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    tmp.replace(out_file)
    return str(out_file)


@session_locked
def analyze_session_gray_box(session_id: str) -> dict:
    payload = load_session(session_id)
    folder = session_dir(session_id)
    source_path = folder / "source.py"
    if not source_path.is_file():
        raise FileNotFoundError(f"source.py not found for session '{session_id}'.")

    requirements = (payload.get("requirement_analysis") or {}).get("requirements") or []
    structured = [
        {
            "requirement_id": str(item.get("requirement_id") or "").strip(),
            "condition": str(item.get("condition") or "").strip(),
            "expected_result": str(item.get("expected_result") or "").strip(),
        }
        for item in requirements
        if isinstance(item, dict) and item.get("requirement_id")
    ]
    if not structured:
        raise GrayBoxError("Run requirement analysis (Task 4) before gray-box test generation.")

    source_code = source_path.read_text(encoding="utf-8")
    public_api = _public_api_catalog(payload, source_code)
    if not public_api:
        raise GrayBoxError("No public top-level functions found for gray-box testing.")
    functions = (payload.get("code_analysis") or {}).get("functions") or []
    if not functions:
        raise GrayBoxError("Run code analysis (Task 3) before gray-box test generation.")

    source = "fallback"
    try:
        if llm_is_configured():
            cases = _generate_cases_with_llm(
                structured_requirements=structured,
                public_api=public_api,
                functions=functions,
                source_code=source_code,
                api_key=NVIDIA_API_KEY.strip(),
                model_name=NVIDIA_MODEL,
            )
            source = "llm"
        else:
            cases = _fallback_cases(structured, public_api, functions, source_code)
    except Exception:
        try:
            cases = _fallback_cases(structured, public_api, functions, source_code)
            source = "heuristic-fallback"
        except Exception as exc:
            raise GrayBoxError(str(exc)) from exc

    if not cases:
        raise GrayBoxError("No gray-box test cases could be generated.")

    file_path = _write_pytest_file(session_id, cases)
    result = {
        "test_count": len(cases),
        "requirement_count": len(structured),
        "function_count": len(public_api),
        "generation_source": source,
        "files_written": [file_path],
        "test_cases": cases,
    }
    try:
        payload["gray_box_tests"] = result
        payload["status"] = "gray_box_generated"
        save_session(payload)
        return payload
    except Exception as exc:  # noqa: BLE001
        log_session_error(session_id, "gray_box", exc)
        raise GrayBoxError(str(exc)) from exc
