"""Task 6 — Black Box Test Case Generator (requirements + public API only)."""

from __future__ import annotations

import ast
import json
import re
from typing import Any, Callable

from config import NVIDIA_API_KEY, NVIDIA_MODEL
from llm_client import generate_text, llm_is_configured
from input_handler.handler import load_session, save_session, session_dir
from input_handler.session_logging import log_session_error
from test_generation.prompts_black_box import PROMPT_TEMPLATE, STRICT_RETRY_PROMPT


class BlackBoxError(Exception):
    """Raised when black-box test generation fails."""


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


def _public_api_from_ast(source_code: str) -> list[dict[str, Any]]:
    tree = ast.parse(source_code)
    catalog: list[dict[str, Any]] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        params = []
        for arg in node.args.args:
            if arg.arg in {"self", "cls"}:
                continue
            annotation = ast.unparse(arg.annotation) if arg.annotation else None
            params.append({"name": arg.arg, "annotation": annotation})
        return_type = ast.unparse(node.returns) if node.returns else None
        catalog.append(
            {
                "name": node.name,
                "qualified_name": node.name,
                "params": params,
                "return_type": return_type,
            }
        )
    return catalog


def _public_api_catalog(payload: dict, source_code: str) -> list[dict[str, Any]]:
    functions = (payload.get("code_analysis") or {}).get("functions") or []
    catalog: list[dict[str, Any]] = []
    for fn in functions:
        if fn.get("is_async"):
            continue
        qualified = fn.get("qualified_name") or fn.get("name") or ""
        if "." in qualified:
            continue
        catalog.append(
            {
                "name": fn["name"],
                "qualified_name": qualified,
                "params": fn.get("params") or [],
                "return_type": fn.get("return_type"),
            }
        )
    if catalog:
        return catalog
    return _public_api_from_ast(source_code)


def _default_inputs_for_params(params: list[dict[str, Any]]) -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    for param in params:
        name = param.get("name")
        if not name:
            continue
        annotation = str(param.get("annotation") or "").lower()
        if "bool" in annotation:
            inputs[name] = False
        elif "list" in annotation:
            inputs[name] = []
        elif "int" in annotation:
            inputs[name] = 0
        elif "float" in annotation:
            inputs[name] = 0.0
        elif "str" in annotation:
            inputs[name] = "x"
        else:
            inputs[name] = 0
    return inputs


def _inputs_from_condition(condition: str, params: list[dict[str, Any]]) -> dict[str, Any]:
    inputs = _default_inputs_for_params(params)
    lowered = condition.lower()
    for key in list(inputs.keys()):
        if key in lowered:
            if isinstance(inputs[key], bool):
                inputs[key] = "member" in lowered or "true" in lowered
            elif isinstance(inputs[key], (int, float)) and "negative" in lowered:
                inputs[key] = -1
            elif isinstance(inputs[key], list) and "empty" in lowered:
                inputs[key] = []
    if "member" in lowered:
        for key, value in inputs.items():
            if isinstance(value, bool) and "member" in key.lower():
                inputs[key] = True
            elif isinstance(value, bool) and key in {"is_member", "member"}:
                inputs[key] = True
    for key in inputs:
        if key == "is_member" and "member" in lowered and "non-member" not in lowered:
            inputs[key] = "non-member" not in lowered
        if key == "price" and isinstance(inputs[key], (int, float)):
            inputs[key] = 100.0
    return inputs


def _pick_function_for_requirement(
    requirement: dict[str, str], catalog: list[dict[str, Any]], index: int
) -> str | None:
    if not catalog:
        return None
    blob = f"{requirement.get('condition', '')} {requirement.get('expected_result', '')}".lower()
    for entry in catalog:
        name = entry["name"].lower()
        if name in blob or name.replace("_", " ") in blob:
            return entry["name"]
    return catalog[index % len(catalog)]["name"]


def _normalize_cases(
    data: Any,
    requirement_ids: set[str],
    allowed_functions: set[str],
) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        raise BlackBoxError("LLM JSON root must be an object.")
    items = data.get("test_cases")
    if not isinstance(items, list) or not items:
        raise BlackBoxError("No black-box test cases returned.")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise BlackBoxError(f"Test case {index} must be an object.")
        req_id = str(item.get("requirement_id") or "").strip()
        if req_id not in requirement_ids:
            raise BlackBoxError(f"Test case {index} has unknown requirement_id '{req_id}'.")
        function_name = str(item.get("function_name") or "").strip()
        if function_name not in allowed_functions:
            raise BlackBoxError(
                f"Test case {index} references unknown function '{function_name}'."
            )
        inputs = item.get("input")
        if not isinstance(inputs, dict):
            raise BlackBoxError(f"Test case {index} must include an 'input' object.")
        expected_output = item.get("expected_output")
        expected_exception = item.get("expected_exception")
        if expected_exception is None and "expected_output" not in item:
            raise BlackBoxError(
                f"Test case {index} needs expected_output or expected_exception."
            )
        normalized.append(
            {
                "case_id": str(item.get("case_id") or f"bb{index}"),
                "description": str(item.get("description") or f"Black-box case {index}"),
                "requirement_id": req_id,
                "function_name": function_name,
                "input": inputs,
                "expected_output": expected_output,
                "expected_exception": str(expected_exception).strip()
                if expected_exception
                else None,
                "test_type": "black_box",
            }
        )
    return normalized


def _generate_cases_with_llm(
    *,
    requirements_text: str,
    structured_requirements: list[dict[str, str]],
    public_api: list[dict[str, Any]],
    api_key: str,
    model_name: str,
    llm_call: Callable[..., str] = _call_llm,
) -> list[dict[str, Any]]:
    requirement_ids = {req["requirement_id"] for req in structured_requirements}
    allowed_functions = {entry["name"] for entry in public_api}
    prompt = (
        PROMPT_TEMPLATE.replace("<<<REQUIREMENTS_TEXT>>>", requirements_text)
        .replace("<<<STRUCTURED_REQUIREMENTS>>>", json.dumps(structured_requirements, indent=2))
        .replace("<<<PUBLIC_API>>>", json.dumps(public_api, indent=2))
    )
    raw = ""
    try:
        raw = llm_call(prompt, api_key, model_name)
        return _normalize_cases(_extract_json(raw), requirement_ids, allowed_functions)
    except (json.JSONDecodeError, BlackBoxError, TypeError, ValueError):
        retry = (
            prompt
            + "\n\n"
            + STRICT_RETRY_PROMPT
            + "\n\nPrevious invalid output:\n"
            + (raw[:4000] if raw else "(empty)")
        )
        raw = llm_call(retry, api_key, model_name)
        return _normalize_cases(_extract_json(raw), requirement_ids, allowed_functions)


def _fallback_cases(
    structured_requirements: list[dict[str, str]],
    public_api: list[dict[str, Any]],
    source_code: str,
) -> list[dict[str, Any]]:
    namespace: dict[str, Any] = {}
    try:
        exec(compile(source_code, "<source>", "exec"), namespace)
    except Exception:
        namespace = {}

    name_to_params = {entry["name"]: entry.get("params") or [] for entry in public_api}
    cases: list[dict[str, Any]] = []

    for index, requirement in enumerate(structured_requirements):
        function_name = _pick_function_for_requirement(requirement, public_api, index)
        if not function_name:
            continue
        params = name_to_params.get(function_name, [])
        inputs = _inputs_from_condition(requirement["condition"], params)
        target = namespace.get(function_name)
        condition_lower = requirement["condition"].lower()
        expected_exception = None
        if "error" in condition_lower or "reject" in condition_lower:
            expected_exception = "ValueError"
            cases.append(
                {
                    "case_id": f"bb-req-{index + 1}",
                    "description": requirement["condition"],
                    "requirement_id": requirement["requirement_id"],
                    "function_name": function_name,
                    "input": inputs,
                    "expected_output": None,
                    "expected_exception": expected_exception,
                    "test_type": "black_box",
                    "source": "heuristic-fallback",
                }
            )
            continue

        expected_output: Any = None
        if callable(target):
            try:
                expected_output = target(**inputs)
            except Exception as exc:
                cases.append(
                    {
                        "case_id": f"bb-req-{index + 1}",
                        "description": requirement["condition"],
                        "requirement_id": requirement["requirement_id"],
                        "function_name": function_name,
                        "input": inputs,
                        "expected_output": None,
                        "expected_exception": type(exc).__name__,
                        "test_type": "black_box",
                        "source": "heuristic-fallback",
                    }
                )
                continue

        cases.append(
            {
                "case_id": f"bb-req-{index + 1}",
                "description": requirement["condition"],
                "requirement_id": requirement["requirement_id"],
                "function_name": function_name,
                "input": inputs,
                "expected_output": expected_output,
                "expected_exception": None,
                "test_type": "black_box",
                "source": "heuristic-fallback",
            }
        )

    if not cases:
        raise BlackBoxError("Heuristic black-box generator produced no cases.")
    return cases


def _write_pytest_file(session_id: str, cases: list[dict[str, Any]]) -> str:
    out_dir = session_dir(session_id) / "tests" / "black_box"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "test_black_box.py"

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
        function_name = case["function_name"]
        safe_req = re.sub(r"[^a-zA-Z0-9_]+", "_", req_id)
        test_name = f"test_black_box_{safe_req}_case{index}"
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

    content = "\n".join(lines)
    tmp = out_file.with_suffix(out_file.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(out_file)
    return str(out_file)


def analyze_session_black_box(session_id: str) -> dict:
    payload = load_session(session_id)
    folder = session_dir(session_id)
    source_path = folder / "source.py"
    if not source_path.is_file():
        raise FileNotFoundError(f"source.py not found for session '{session_id}'.")

    requirements = (payload.get("requirement_analysis") or {}).get("requirements") or []
    structured: list[dict[str, str]] = [
        {
            "requirement_id": str(item.get("requirement_id") or "").strip(),
            "condition": str(item.get("condition") or "").strip(),
            "expected_result": str(item.get("expected_result") or "").strip(),
        }
        for item in requirements
        if isinstance(item, dict) and item.get("requirement_id")
    ]
    if not structured:
        raise BlackBoxError(
            "Run requirement analysis (Task 4) before black-box test generation."
        )

    requirement_ids = {item["requirement_id"] for item in structured}
    requirements_text = str(payload.get("requirements_text") or "").strip()
    source_code = source_path.read_text(encoding="utf-8")
    public_api = _public_api_catalog(payload, source_code)
    if not public_api:
        raise BlackBoxError("No public top-level functions found for black-box testing.")

    source = "fallback"
    try:
        if llm_is_configured():
            cases = _generate_cases_with_llm(
                requirements_text=requirements_text,
                structured_requirements=structured,
                public_api=public_api,
                api_key=NVIDIA_API_KEY.strip(),
                model_name=NVIDIA_MODEL,
            )
            source = "llm"
        else:
            cases = _fallback_cases(structured, public_api, source_code)
    except Exception:
        cases = _fallback_cases(structured, public_api, source_code)
        source = "heuristic-fallback"

    file_path = _write_pytest_file(session_id, cases)
    per_requirement: dict[str, list[dict[str, Any]]] = {rid: [] for rid in requirement_ids}
    for case in cases:
        per_requirement.setdefault(case["requirement_id"], []).append(case)

    requirement_summaries = [
        {
            "requirement_id": req_id,
            "case_count": len(per_requirement.get(req_id, [])),
            "cases": per_requirement.get(req_id, []),
        }
        for req_id in sorted(requirement_ids)
    ]

    result = {
        "test_count": len(cases),
        "requirement_count": len(structured),
        "generation_source": source,
        "files_written": [file_path],
        "requirements": requirement_summaries,
        "test_cases": cases,
    }

    try:
        payload["black_box_tests"] = result
        payload["status"] = "black_box_generated"
        save_session(payload)
        return payload
    except Exception as exc:  # noqa: BLE001
        log_session_error(session_id, "black_box", exc)
        raise BlackBoxError(str(exc)) from exc
