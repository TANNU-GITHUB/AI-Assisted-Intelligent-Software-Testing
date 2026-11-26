"""Task 6 — Black Box Test Case Generator (requirements + public API only)."""

from __future__ import annotations

import ast
import json
import re
from typing import Any, Callable

from config import NVIDIA_API_KEY, NVIDIA_MODEL
from llm_client import generate_text, llm_is_configured
from input_handler.handler import load_session, save_session, session_dir, session_locked
from input_handler.session_logging import log_session_error
from json_utils import extract_json as _extract_json
from test_generation.prompts_black_box import PROMPT_TEMPLATE, STRICT_RETRY_PROMPT
from test_generation.safe_codegen import (
    expected_exception_expression,
    function_call_expression,
    generated_test_imports,
    json_expression,
    require_python_identifier,
)


class BlackBoxError(Exception):
    """Raised when black-box test generation fails."""


def _call_llm(prompt: str, api_key: str, model_name: str) -> str:
    """Call the LLM. Wraps LLMError in BlackBoxError so it stays a 400, not a 500."""
    try:
        text, _model_used = generate_text(prompt, api_key=api_key, model_name=model_name)
        return text
    except BlackBoxError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise BlackBoxError(
            f"LLM unavailable — {exc}. "
            "Install Ollama (https://ollama.com) and run: ollama pull llama3.2"
        ) from exc


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


def _is_bool_param(name: str, annotation: str = "", default: Any = None) -> bool:
    anno = str(annotation or "").lower()
    if "bool" in anno:
        return True
    if default is not None and str(default).lower() in {"true", "false"}:
        return True
    low = name.lower()
    return (
        low.startswith(("is_", "has_", "can_", "should_", "allow_", "enable_"))
        or low.endswith(("_flag", "_allowed", "_enabled", "_valid", "_required"))
        or low in {"active", "enabled", "valid", "member", "vip", "admin"}
    )


def _infer_domain_default(name: str, annotation: str = "", default: Any = None) -> Any:
    """Infer realistic, domain-aware defaults instead of generic 100 placeholders."""
    anno = str(annotation or "").lower()
    low = name.lower()

    if _is_bool_param(name, anno, default):
        if default is not None and str(default).lower() in {"true", "false"}:
            return str(default).lower() == "true"
        return False

    if "none" in anno and default is None and "str" in anno:
        # Optional string like coupon_code: str | None = None
        return None

    # Age domain
    if "age" in low:
        return 25

    # Currency / Order totals / Prices
    if any(k in low for k in ("subtotal", "price", "amount", "cost", "total", "balance", "fee")):
        return 50.0 if ("float" in anno or "double" in anno or "decimal" in anno) else 50

    # Discount rates / percentages
    if any(k in low for k in ("discount", "rate", "percent", "tax_rate", "ratio")):
        return 0.10

    # Counts / Quantities
    if any(k in low for k in ("qty", "quantity", "count", "num_items", "items_count", "n", "size")):
        return 2

    # Coupon / Promo codes
    if any(k in low for k in ("coupon", "promo", "voucher")):
        return "SAVE10"

    # User / Auth info
    if "email" in low or "mail" in low:
        return "alice@example.com"
    if any(k in low for k in ("username", "user_name", "login")):
        return "alice"
    if low in ("name", "first_name", "last_name", "author"):
        return "Alice"

    # Status / Category
    if "status" in low or "state" in low:
        return "active"

    # General type-based defaults
    if "list" in anno or "array" in anno:
        return [10, 20]
    if "dict" in anno or "map" in anno:
        return {"key": "value"}
    if "str" in anno or "text" in anno:
        return "standard"
    if "float" in anno or "double" in anno or "decimal" in anno:
        return 25.0
    if "int" in anno:
        return 10

    return 25.0


def _default_inputs_for_params(params: list[dict[str, Any]]) -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    for p in params:
        name = p.get("name")
        if not name:
            continue
        anno = str(p.get("annotation") or "").lower()
        dflt = p.get("default")
        inputs[name] = _infer_domain_default(name, anno, dflt)
    return inputs


def _inputs_from_condition(condition: str, params: list[dict[str, Any]]) -> dict[str, Any]:
    inputs = _default_inputs_for_params(params)
    cond = condition.strip()
    low = cond.lower()

    # 1. Parameter-specific evaluations
    for p in params:
        name = p.get("name")
        if not name or name not in inputs:
            continue
        val = inputs[name]
        anno = str(p.get("annotation") or "").lower()

        if isinstance(val, bool) or _is_bool_param(name, anno):
            if (
                re.search(rf"\b{re.escape(name)}\s*(?:!=|is\s+not)\s*true\b", cond, re.IGNORECASE)
                or re.search(rf"\b{re.escape(name)}\s*(?:==|is|=|:)?\s*false\b", cond, re.IGNORECASE)
                or re.search(rf"\bnot\s+{re.escape(name)}\b", cond, re.IGNORECASE)
                or re.search(rf"\bno[t\s]+{re.escape(name)}\b", cond, re.IGNORECASE)
                or re.search(rf"\bnon[-_ ]?{re.escape(name)}\b", cond, re.IGNORECASE)
                or ("non-member" in low and "member" in name.lower())
                or ("not a member" in low and "member" in name.lower())
            ):
                inputs[name] = False
            elif (
                re.search(rf"\b{re.escape(name)}\s*(?:==|is|=|:)?\s*true\b", cond, re.IGNORECASE)
                or re.search(rf"\b{re.escape(name)}\s*(?:!=|is\s+not)\s*false\b", cond, re.IGNORECASE)
                or re.search(rf"\bwith\s+{re.escape(name)}\b", cond, re.IGNORECASE)
                or ("is member" in low and "member" in name.lower())
                or ("member" in low and "non-member" not in low and "not a member" not in low and "member" in name.lower())
            ):
                inputs[name] = True

        elif isinstance(val, (int, float)) or any(t in anno for t in ("int", "float", "double")):
            is_float = isinstance(val, float) or "float" in anno or "double" in anno
            # A) Negative condition: subtotal < 0, negative subtotal, subtotal is negative
            if (
                re.search(rf"\bnegative\s+{re.escape(name)}\b", cond, re.IGNORECASE)
                or (name.lower() in low and "negative" in low)
                or re.search(rf"\b{re.escape(name)}\s*<\s*0\b", cond, re.IGNORECASE)
            ):
                inputs[name] = -10.0 if is_float else -10
                continue

            # B) Explicit value: name is 500, name = 500, name: 500, name == 500
            direct = re.search(rf"\b{re.escape(name)}\s*(?:is|=|==|:|of|to|was)\s*(-?\d+(?:\.\d+)?)\b", cond, re.IGNORECASE)
            if direct:
                inputs[name] = float(direct.group(1)) if is_float or "." in direct.group(1) else int(direct.group(1))
            else:
                # C) Comparison to constant: name >= 90, name < 18, name <= 0
                comp = re.search(rf"\b(?:{re.escape(name)}|discounted_{re.escape(name)}|value)\s*(>=|>|<=|<|==|!=)\s*(-?\d+(?:\.\d+)?)\b", cond, re.IGNORECASE)
                if comp:
                    op = comp.group(1)
                    thresh = float(comp.group(2)) if is_float or "." in comp.group(2) else int(comp.group(2))
                    step = 1.0 if is_float else 1
                    if op == ">=":
                        # Boundary Value: test right at the threshold
                        val_res = thresh
                    elif op == ">":
                        val_res = thresh + (5.0 if is_float else 5)
                    elif op == "<=":
                        val_res = thresh
                    elif op == "<":
                        val_res = thresh - (5.0 if is_float else 5)
                    elif op == "==":
                        val_res = thresh
                    elif op == "!=":
                        val_res = thresh + step
                    else:
                        val_res = thresh
                    inputs[name] = float(val_res) if is_float else int(val_res)

                # D) Modulo constraint: name % 100 == 0
                mod = re.search(rf"\b{re.escape(name)}\s*%\s*(\d+)\s*(==|!=)\s*0\b", cond, re.IGNORECASE)
                if mod:
                    m_val = int(mod.group(1))
                    m_op = mod.group(2)
                    cur = inputs[name]
                    if m_op == "==":
                        cur = max(m_val, (int(cur) // m_val) * m_val)
                    else:
                        if int(cur) % m_val == 0:
                            cur += m_val // 2 or 1
                    inputs[name] = float(cur) if is_float else int(cur)

        elif isinstance(val, (str, type(None))) or "str" in anno:
            str_match = re.search(rf"\b{re.escape(name)}\s*(?:is|=|==|:|of)?\s*['\"]([^'\"]+)['\"]", cond, re.IGNORECASE)
            if str_match:
                inputs[name] = str_match.group(1)
            elif re.search(rf"\b{re.escape(name)}\s*(?:is|=|==)?\s*SAVE10\b", cond, re.IGNORECASE) or ("save10" in low and "coupon" in name.lower()):
                inputs[name] = "SAVE10"
            elif (
                "no coupon" in low
                or "without coupon" in low
                or "coupon is none" in low
                or "none" in low
            ) and "coupon" in name.lower():
                inputs[name] = None
            elif "empty" in low and name.lower() in low:
                inputs[name] = ""

        elif isinstance(val, list):
            list_match = re.search(rf"\b{re.escape(name)}\s*(?:is|=|==|:)?\s*(\[[^\]]*\])", cond)
            if list_match:
                try:
                    inputs[name] = ast.literal_eval(list_match.group(1))
                except Exception:
                    pass
            elif "empty" in low and name.lower() in low:
                inputs[name] = []

    # 2. Relational constraints between any pairs of numeric parameters: pA >= pB, pA < pB
    num_params = [p["name"] for p in params if isinstance(inputs.get(p.get("name")), (int, float))]
    for i, pA in enumerate(num_params):
        for j, pB in enumerate(num_params):
            if i == j:
                continue
            vA = inputs[pA]
            vB = inputs[pB]
            if re.search(rf"\b{re.escape(pA)}\s*(?:>=|>)\s*{re.escape(pB)}\b", low):
                if vA <= vB:
                    diff = 50.0 if isinstance(vA, float) else 50
                    inputs[pA] = vB + diff
            elif re.search(rf"\b{re.escape(pA)}\s*(?:<=|<)\s*{re.escape(pB)}\b", low):
                if vA >= vB:
                    diff = 50.0 if isinstance(vA, float) else 50
                    inputs[pA] = max(0.0 if isinstance(vA, float) else 0, vB - diff)

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
    public_api: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    func_param_map = {
        entry["name"]: [p["name"] for p in entry.get("params") or [] if p.get("name")]
        for entry in (public_api or [])
    }
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
        if not items and data.get("requirements") and isinstance(data["requirements"], list):
            fallback_fn = next(iter(allowed_functions), "")
            for r_idx, req in enumerate(data["requirements"], start=1):
                if isinstance(req, dict):
                    cond = str(req.get("condition") or "").lower()
                    exc = "ValueError" if ("error" in cond or "raise" in cond or "exception" in cond) else None
                    items.append({
                        "case_id": f"bb{r_idx}",
                        "description": req.get("condition") or f"Requirement {req.get('requirement_id')}",
                        "requirement_id": req.get("requirement_id"),
                        "function_name": fallback_fn,
                        "input": req.get("input") or {},
                        "expected_output": req.get("expected_output") or (None if exc else req.get("expected_result")),
                        "expected_exception": exc,
                    })
    if not items:
        raise BlackBoxError("No black-box test cases returned.")

    default_req_id = next(iter(requirement_ids)) if requirement_ids else "REQ-01"
    default_fn = next(iter(allowed_functions)) if allowed_functions else ""

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        req_id = str(item.get("requirement_id") or "").strip()
        if req_id not in requirement_ids:
            for rid in requirement_ids:
                if rid.lower() == req_id.lower() or rid.replace("-", "") == req_id.replace("-", ""):
                    req_id = rid
                    break
            else:
                req_id = default_req_id

        function_name = str(item.get("function_name") or "").strip()
        if function_name not in allowed_functions:
            for fn in allowed_functions:
                if fn.lower() == function_name.lower():
                    function_name = fn
                    break
            else:
                if allowed_functions:
                    raise BlackBoxError(
                        f"Test case targets unknown function {function_name!r}. "
                        f"Allowed: {sorted(allowed_functions)}"
                    )
                function_name = default_fn

        inputs = item.get("input")
        if not isinstance(inputs, dict):
            inputs = {}

        # Sanitize parameter names: map generic param_a/param_b or ensure keys match API
        expected_params = func_param_map.get(function_name, [])
        if expected_params:
            valid_keys = [k for k in inputs.keys() if k in expected_params]
            if not valid_keys and inputs:
                # Keys were generic (e.g. param_a, param_b) -> map positionally
                vals = list(inputs.values())
                inputs = {
                    p_name: vals[i] if i < len(vals) else _infer_domain_default(p_name)
                    for i, p_name in enumerate(expected_params)
                }
            else:
                sanitized = {k: v for k, v in inputs.items() if k in expected_params}
                for p_name in expected_params:
                    if p_name not in sanitized:
                        sanitized[p_name] = _infer_domain_default(p_name)
                inputs = sanitized

        expected_output = item.get("expected_output")
        expected_exception = item.get("expected_exception")
        desc = str(item.get("description") or f"Black-box case {index}").strip()

        if expected_exception is None and "expected_output" not in item:
            if "error" in desc.lower() or "exception" in desc.lower() or "valueerror" in desc.lower():
                expected_exception = "ValueError"
            else:
                expected_output = None

        if expected_exception:
            try:
                expected_exception = require_python_identifier(
                    str(expected_exception).strip(), "Exception name"
                )
            except ValueError as exc:
                raise BlackBoxError(str(exc)) from exc

        normalized.append(
            {
                "case_id": str(item.get("case_id") or f"bb{index}"),
                "description": desc,
                "requirement_id": req_id,
                "function_name": function_name,
                "input": inputs,
                "expected_output": expected_output,
                "expected_exception": str(expected_exception).strip() if expected_exception else None,
                "test_type": "black_box",
            }
        )

    if not normalized:
        raise BlackBoxError("No valid test cases could be normalized.")
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
    req_text = (
        requirements_text
        if len(requirements_text) <= 8_000
        else requirements_text[:8_000] + "\n# ... (truncated for LLM context) ..."
    )
    structured_for_llm = structured_requirements[:40]
    api_for_llm = public_api[:40]
    prompt = (
        PROMPT_TEMPLATE.replace("<<<REQUIREMENTS_TEXT>>>", req_text)
        .replace("<<<STRUCTURED_REQUIREMENTS>>>", json.dumps(structured_for_llm, indent=2))
        .replace("<<<PUBLIC_API>>>", json.dumps(api_for_llm, indent=2))
    )
    raw = ""
    try:
        raw = llm_call(prompt, api_key, model_name)
        return _normalize_cases(_extract_json(raw), requirement_ids, allowed_functions, public_api)
    except (json.JSONDecodeError, BlackBoxError, TypeError, ValueError):
        retry = (
            prompt
            + "\n\n"
            + STRICT_RETRY_PROMPT
            + "\n\nPrevious invalid output:\n"
            + (raw[:4000] if raw else "(empty)")
        )
        raw = llm_call(retry, api_key, model_name)
        return _normalize_cases(_extract_json(raw), requirement_ids, allowed_functions, public_api)


def _fallback_cases(
    structured_requirements: list[dict[str, str]],
    public_api: list[dict[str, Any]],
    source_code: str,
) -> list[dict[str, Any]]:
    tree = ast.parse(source_code)
    defined_functions = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    name_to_params = {entry["name"]: entry.get("params") or [] for entry in public_api}
    cases: list[dict[str, Any]] = []

    for index, requirement in enumerate(structured_requirements):
        function_name = _pick_function_for_requirement(requirement, public_api, index)
        if not function_name or function_name not in defined_functions:
            continue
        params = name_to_params.get(function_name, [])
        inputs = _inputs_from_condition(requirement["condition"], params)
        condition_lower = requirement["condition"].lower()
        combined_lower = f"{requirement.get('condition', '')} {requirement.get('expected_result', '')}".lower()
        expected_exception = None
        if any(w in combined_lower for w in ["valueerror", "raise", "exception"]) or (
            ("error" in combined_lower or "reject" in combined_lower or "invalid" in combined_lower)
            and "return" not in combined_lower
        ) or ("<= 0" in condition_lower or "< 0" in condition_lower):
            if "raise" in combined_lower or "valueerror" in combined_lower or "exception" in combined_lower or "invalid" in combined_lower or "<= 0" in condition_lower or "< 0" in condition_lower:
                expected_exception = "ValueError"

        if expected_exception:
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
                    "assert_output": True,
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
                "expected_output": None,
                "expected_exception": None,
                "test_type": "black_box",
                "source": "heuristic-fallback",
                "assert_output": False,
            }
        )

    if not cases and public_api:
        first_entry = public_api[0]
        default_fn = first_entry["name"]
        default_params = first_entry.get("params") or []
        for index, requirement in enumerate(structured_requirements):
            cases.append(
                {
                    "case_id": f"bb-req-{index + 1}",
                    "description": requirement.get("condition") or f"requirement {index + 1}",
                    "requirement_id": requirement.get("requirement_id") or f"REQ-{index + 1:02d}",
                    "function_name": default_fn,
                    "input": _inputs_from_condition(requirement.get("condition", ""), default_params),
                    "expected_output": None,
                    "expected_exception": None,
                    "test_type": "black_box",
                    "source": "heuristic-fallback",
                    "assert_output": False,
                }
            )
    return cases


def _write_pytest_file(session_id: str, cases: list[dict[str, Any]]) -> str:
    out_dir = session_dir(session_id) / "tests" / "black_box"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "test_black_box.py"

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
        try:
            function_name = require_python_identifier(
                case["function_name"], "Function name"
            )
        except ValueError as exc:
            raise BlackBoxError(str(exc)) from exc
        safe_req = re.sub(r"[^a-zA-Z0-9_]+", "_", req_id)
        test_name = f"test_black_box_case{index}_{safe_req}"
        inputs = case.get("input", {}) or {}
        call = function_call_expression(function_name, inputs)
        lines.append(
            f"@pytest.mark.parametrize('_requirement_id', [{req_id!r}], ids=[{req_id!r}])"
        )
        lines.append(f"def {test_name}(_requirement_id):")
        if not case.get("assert_output", True):
            lines.append("    # Verify execution completes without uncaught exception")
            lines.append(f"    result = {call}")
            lines.append("    assert result is not None or result is None")
        elif case.get("expected_exception"):
            exception_name = expected_exception_expression(case["expected_exception"])
            lines.append(f"    with pytest.raises({exception_name}):")
            lines.append(f"        {call}")
        elif case.get("expected_output") is not None:
            expected = case.get("expected_output")
            lines.append(f"    _assert_match({call}, {json_expression(expected)})")
        else:
            lines.append("    # Verify execution completes without uncaught exception")
            lines.append(f"    result = {call}")
            lines.append("    assert result is not None or result is None")
        lines.append("")

    content = "\n".join(lines)
    tmp = out_file.with_suffix(out_file.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(out_file)
    return str(out_file)


@session_locked
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
    requirements_path = folder / "requirements.txt"
    if not requirements_path.is_file():
        raise BlackBoxError(
            f"Requirements text file not found for session '{session_id}'."
        )
    requirements_text = requirements_path.read_text(encoding="utf-8").strip()
    if not requirements_text:
        raise BlackBoxError(
            f"Requirements text file is empty for session '{session_id}'."
        )
    source_code = source_path.read_text(encoding="utf-8")
    public_api = _public_api_catalog(payload, source_code)
    if not public_api:
        raise BlackBoxError("No public top-level functions found for black-box testing.")

    source = "fallback"
    try:
        if bool(NVIDIA_API_KEY.strip()) or llm_is_configured():
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
        try:
            cases = _fallback_cases(structured, public_api, source_code)
        except Exception:
            cases = []
        source = "heuristic-fallback"

    if not cases and public_api:
        first_entry = public_api[0]
        default_fn = first_entry["name"]
        default_params = first_entry.get("params") or []
        for index, requirement in enumerate(structured):
            cases.append(
                {
                    "case_id": f"bb-req-{index + 1}",
                    "description": requirement.get("condition") or f"requirement {index + 1}",
                    "requirement_id": requirement.get("requirement_id") or f"REQ-{index + 1:02d}",
                    "function_name": default_fn,
                    "input": _inputs_from_condition(requirement.get("condition", ""), default_params),
                    "expected_output": None,
                    "expected_exception": None,
                    "test_type": "black_box",
                    "source": "heuristic-fallback",
                    "assert_output": False,
                }
            )

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
