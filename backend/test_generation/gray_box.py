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
)
from test_generation.prompts_gray_box import PROMPT_TEMPLATE
from test_generation.safe_codegen import (
    expected_exception_expression,
    function_call_expression,
    generated_test_imports,
    json_expression,
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
) -> list[dict[str, Any]]:
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

        req_id = str(item.get("requirement_id") or "").strip()
        if req_id not in requirement_ids:
            req_id = sorted(requirement_ids)[index % len(requirement_ids)] if requirement_ids else "REQ-01"

        function_name = str(item.get("function_name") or "").strip()
        if function_name not in allowed_functions:
            if allowed_functions:
                function_name = sorted(allowed_functions)[index % len(allowed_functions)]
            else:
                continue

        inputs = item.get("input")
        if not isinstance(inputs, dict):
            inputs = {}
        expected_exception = item.get("expected_exception")
        if expected_exception:
            try:
                require_python_identifier(str(expected_exception), "Exception name")
            except ValueError:
                expected_exception = "ValueError"

        normalized.append({
            "case_id": str(item.get("case_id") or f"gray{index}").strip(),
            "description": str(item.get("description") or f"Gray-box case {index}").strip(),
            "requirement_id": req_id,
            "function_name": function_name,
            "input": inputs,
            "expected_output": item.get("expected_output"),
            "expected_exception": str(expected_exception).strip() if expected_exception else None,
            "target_branch": str(item.get("target_branch") or "").strip(),
            "test_type": "gray_box",
        })
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
        structured_requirements=json.dumps(structured_requirements[:40], indent=2),
        public_api=json.dumps(public_api[:40], indent=2),
        branch_map=json.dumps([
            {
                "function": fn["name"],
                "branches": fn.get("branches") or [],
                "cyclomatic_complexity": fn.get("cyclomatic_complexity"),
            }
            for fn in functions[:40]
        ], indent=2),
        source_context=source_code[:20_000],
    )
    raw = llm_call(prompt, api_key, model_name)
    return _normalize_cases(extract_json(raw), requirement_ids, allowed_functions)


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
            "requirement": case.get("requirement_id"),
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
            req_id = (
                structured_requirements[index % len(structured_requirements)]["requirement_id"]
                if structured_requirements
                else "REQ-01"
            )
            case = dict(case)
            case["test_type"] = "gray_box"
            case["requirement_id"] = req_id
            branch = case.get("description") or f"branch {index}"
            case["target_branch"] = branch
            signature = json.dumps({
                "function": case.get("function_name"),
                "input": case.get("input"),
                "requirement": req_id,
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
        if not case.get("assert_output", True) and "expected_output" not in case:
            lines.append('    pytest.skip("Static fallback cannot determine the expected output.")')
        elif case.get("expected_exception"):
            exception_name = expected_exception_expression(case["expected_exception"])
            lines.append(f"    with pytest.raises({exception_name}):")
            lines.append(f"        {call}")
        else:
            expected = case.get("expected_output")
            lines.append(f"    _assert_match({call}, {json_expression(expected)})")
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
