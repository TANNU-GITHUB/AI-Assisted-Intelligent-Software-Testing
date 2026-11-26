"""Task 6 — Black Box Test Case Generator (requirements + public API only)."""

from __future__ import annotations

import ast
import json
import re
from typing import Any, Callable

from config import NVIDIA_API_KEY, NVIDIA_MODEL
from llm_client import LLMError, generate_text, is_nvidia_exhausted, llm_is_configured
from input_handler.handler import load_session, save_session, session_dir, session_locked
from input_handler.session_logging import log_session_error
from json_utils import extract_json as _extract_json
from test_generation.prompts_black_box import PROMPT_TEMPLATE, STRICT_RETRY_PROMPT
from test_generation.safe_codegen import (
    case_assertion_lines,
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
    tokens = {t for t in re.split(r"[^a-z0-9]+", low) if t}
    is_float = any(t in anno for t in ("float", "double", "decimal")) or (
        isinstance(default, str) and "." in default
    )

    if _is_bool_param(name, anno, default):
        if default is not None and str(default).lower() in {"true", "false"}:
            return str(default).lower() == "true"
        return False

    if "none" in anno and default is None and "str" in anno:
        # Optional string like coupon_code: str | None = None
        return None

    # 1. Collections / Lists must be checked BEFORE scalar numeric types
    if (
        "list" in anno
        or "array" in anno
        or bool(tokens & {"prices", "scores", "items", "numbers", "values", "grades", "data", "cart"})
    ):
        if tokens & {"score", "scores", "mark", "marks", "grade", "grades"}:
            return [60, 90] if ("int" in anno and not is_float) else [60.0, 90.0]
        if tokens & {"gpa", "cgpa"}:
            return [3.0, 3.8]
        if tokens & {"price", "prices", "amount", "cost", "subtotal", "total", "fee"} or any(
            k in low for k in ("price", "amount", "cost", "subtotal", "total", "fee")
        ):
            return [50.0, 100.0]
        return [10.0, 20.0] if is_float else [10, 20]

    if "dict" in anno or "map" in anno or bool(tokens & {"dict", "mapping", "attributes", "metadata", "payload"}):
        return {"key": "value"}

    # 2. Explicit string type annotations (must run before numeric substring heuristics)
    if ("str" in anno or "text" in anno) and not any(t in anno for t in ("int", "float", "double")):
        if "email" in tokens or "mail" in tokens:
            return "alice@example.com"
        if tokens & {"username", "login"} or "user_name" in low:
            return "alice"
        if tokens & {"coupon", "promo", "voucher"}:
            return "SAVE10"
        if tokens & {"status", "state"}:
            return "active"
        if low in ("name", "first_name", "last_name", "author") or tokens & {"name", "author"}:
            return "Alice"
        return "standard"

    # 3. Domain-specific numeric heuristics (using word tokens, not raw single-char substrings)
    if tokens & {"gpa", "cgpa"}:
        return 3.2

    if tokens & {"score", "scores", "mark", "marks", "grade", "grades", "percentage"}:
        return 75.0 if (is_float or not anno) else 75

    if "age" in tokens:
        return 25

    if tokens & {"income", "salary", "wage", "revenue", "budget"} or any(
        k in low for k in ("income", "salary", "wage", "revenue", "budget")
    ):
        return 30000.0 if (is_float or not anno) else 30000

    if tokens & {"subtotal", "price", "amount", "cost", "total", "balance", "fee"} or any(
        k in low for k in ("subtotal", "price", "amount", "cost", "total", "balance", "fee")
    ):
        return 50.0 if is_float else 50

    if tokens & {"discount", "rate", "percent", "ratio"} or "tax_rate" in low or "rate" in tokens:
        return 0.10

    if tokens & {"qty", "quantity", "count", "num_items", "items_count", "size", "n", "k"}:
        return 2

    # 4. Unannotated string domain hints
    if "email" in tokens or "mail" in tokens:
        return "alice@example.com"
    if tokens & {"username", "login"} or "user_name" in low:
        return "alice"
    if tokens & {"coupon", "promo", "voucher"}:
        return "SAVE10"
    if low in ("name", "first_name", "last_name", "author"):
        return "Alice"
    if tokens & {"status", "state", "label", "category"}:
        return "active"

    # 5. General type-based defaults
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


def _param_alias_pattern(name: str, all_names: list[str]) -> str:
    """Build whole-word regex alternatives matching parameter names in prose."""
    low = name.lower()
    variants: list[str] = [low, low.replace("_", " "), f"discounted_{low}"]
    if low.endswith("s") and len(low) > 3:
        variants.append(low[:-1])
    elif not low.endswith("s") and f"{low}s" not in {n.lower() for n in all_names}:
        variants.append(f"{low}s")
    if "_" in low:
        tail = low.split("_")[-1]
        if len(tail) >= 4:
            other_tails = {
                n.lower().split("_")[-1]
                for n in all_names
                if n.lower() != low
            }
            if tail not in other_tails:
                variants.append(tail)
    # Deduplicate and prefer longer phrases first
    uniq = sorted({v for v in variants if v}, key=len, reverse=True)
    return "|".join(re.escape(v) for v in uniq)


def _op_from_phrase(phrase: str) -> str:
    p = re.sub(r"\s+", " ", phrase.strip().lower())
    if p in {"<=", "at or below", "at most", "up to", "no more than", "less than or equal to", "or lower", "or below", "or less"}:
        return "<="
    if p in {">=", "at or above", "at least", "no less than", "greater than or equal to", "or higher", "or above", "or more", "or greater", "+"}:
        return ">="
    if p in {"<", "below", "under", "less than", "lower than", "fewer than"}:
        return "<"
    if p in {">", "above", "over", "greater than", "more than", "higher than", "exceed", "exceeds"}:
        return ">"
    if p == "!=":
        return "!="
    return "=="


def _smart_delta(thresh: float, is_float: bool, low_name: str) -> float | int:
    if "gpa" in low_name or "cgpa" in low_name:
        return 0.5 if thresh in (0.0, 4.0) else 0.2
    if any(k in low_name for k in ("income", "salary", "wage", "budget")):
        return 500.0 if is_float else 500
    if thresh == 0:
        return 5.0 if is_float else 5
    if 0 < abs(thresh) <= 5:
        return 0.5 if is_float else 1
    if 5 < abs(thresh) <= 20:
        return 2.0 if is_float else 2
    return 5.0 if is_float else 5


def _inputs_from_condition(
    condition: str,
    params: list[dict[str, Any]],
    expect_error: bool = False,
) -> dict[str, Any]:
    inputs = _default_inputs_for_params(params)
    cond = condition.strip()
    low = cond.lower()
    all_names = [str(p.get("name") or "") for p in params if p.get("name")]
    explicitly_mutated_for_error = False

    # 1. Parameter-specific evaluations
    for p in params:
        name = p.get("name")
        if not name or name not in inputs:
            continue
        val = inputs[name]
        anno = str(p.get("annotation") or "").lower()
        low_name = name.lower()
        alias_pat = _param_alias_pattern(name, all_names)

        if isinstance(val, list) or "list" in anno or "array" in anno:
            list_match = re.search(rf"\b(?:{alias_pat})\s*(?:is|=|==|:)?\s*(\[[^\]]*\])", cond)
            if list_match:
                try:
                    inputs[name] = ast.literal_eval(list_match.group(1))
                except Exception:
                    pass
            elif (
                "empty" in low
                or re.search(rf"\bnot\s+(?:{alias_pat})\b", low)
                or re.search(rf"\blen\(\s*(?:{alias_pat})\s*\)\s*==\s*0\b", low)
            ):
                inputs[name] = []
                explicitly_mutated_for_error = True
            elif expect_error and (re.search(r"\bnan\b", low) or "not a number" in low):
                inputs[name] = [float("nan")]
                explicitly_mutated_for_error = True
            elif expect_error and (
                "negative" in low or "below 0" in low or "< 0" in low
            ) and any(k in low_name for k in ("score", "price", "mark", "grade", "number", "value")):
                inputs[name] = [-10.0, 50.0] if ("float" in anno or any(isinstance(x, float) for x in val)) else [-10, 50]
                explicitly_mutated_for_error = True
            elif expect_error and (
                "above 100" in low or "> 100" in low
            ) and any(k in low_name for k in ("score", "mark", "grade", "percentage")):
                inputs[name] = [105.0, 80.0]
                explicitly_mutated_for_error = True

        elif isinstance(val, bool) or _is_bool_param(name, anno):
            if (
                re.search(rf"\b(?:{alias_pat})\s*(?:!=|is\s+not)\s*true\b", cond, re.IGNORECASE)
                or re.search(rf"\b(?:{alias_pat})\s*(?:==|is|=|:)?\s*false\b", cond, re.IGNORECASE)
                or re.search(rf"\bnot\s+(?:{alias_pat})\b", cond, re.IGNORECASE)
                or re.search(rf"\bno[t\s]+(?:{alias_pat})\b", cond, re.IGNORECASE)
                or re.search(rf"\bnon[-_ ]?(?:{alias_pat})\b", cond, re.IGNORECASE)
                or ("non-member" in low and "member" in low_name)
                or ("not a member" in low and "member" in low_name)
            ):
                inputs[name] = False
            elif (
                re.search(rf"\b(?:{alias_pat})\s*(?:==|is|=|:)?\s*true\b", cond, re.IGNORECASE)
                or re.search(rf"\b(?:{alias_pat})\s*(?:!=|is\s+not)\s*false\b", cond, re.IGNORECASE)
                or re.search(rf"\bwith\s+(?:{alias_pat})\b", cond, re.IGNORECASE)
                or ("is member" in low and "member" in low_name)
                or ("member" in low and "non-member" not in low and "not a member" not in low and "member" in low_name)
            ):
                inputs[name] = True

        elif isinstance(val, (int, float)) or (
            any(t in anno for t in ("int", "float", "double"))
            and "list" not in anno
            and "dict" not in anno
            and not isinstance(val, (list, dict))
        ):
            is_float = isinstance(val, float) or "float" in anno or "double" in anno
            is_gpa = "gpa" in low_name or "cgpa" in low_name
            is_income = any(k in low_name for k in ("income", "salary", "wage", "budget"))

            # A0) Explicit NaN condition ("Scores that are NAN must raise value error.")
            if re.search(r"\bnan\b", low) or "not a number" in low:
                inputs[name] = float("nan")
                explicitly_mutated_for_error = True
                continue

            # A) Compound violation condition: "below 0 or above 100", "score < 0.0 or score > 100.0"
            out_range = re.search(
                rf"\b(?:{alias_pat})\b[^0-9.\-]{{0,24}}(?:below|under|less\s+than|<)\s*(-?\d+(?:\.\d+)?)\s+or\s+(?:[\w\s]{{0,24}}?)(?:above|over|greater\s+than|more\s+than|>)\s*(-?\d+(?:\.\d+)?)\b",
                cond,
                re.IGNORECASE,
            )
            if out_range:
                low_bound = float(out_range.group(1))
                delta = _smart_delta(low_bound, is_float, low_name)
                res_val = low_bound - delta
                inputs[name] = float(res_val) if is_float else int(res_val)
                explicitly_mutated_for_error = True
                continue

            # B) Negative condition: "negative family income", "subtotal < 0", "income is negative"
            if (
                re.search(rf"\bnegative\s+(?:{alias_pat})\b", cond, re.IGNORECASE)
                or (re.search(rf"\b(?:{alias_pat})\b", low) and "negative" in low)
                or re.search(rf"\b(?:{alias_pat})\s*<\s*0(?:\.0+)?\b", cond, re.IGNORECASE)
            ):
                if is_income:
                    inputs[name] = -1000.0 if is_float else -1000
                elif is_gpa:
                    inputs[name] = -1.0
                else:
                    inputs[name] = -10.0 if is_float else -10
                explicitly_mutated_for_error = True
                continue

            # C) Range phrase: "GPA between 2.0 and 3.69"
            between = re.search(
                rf"\b(?:{alias_pat})\b[^0-9.\-]{{0,20}}\bbetween\s+(-?\d+(?:\.\d+)?)\s+and\s+(-?\d+(?:\.\d+)?)\b",
                cond,
                re.IGNORECASE,
            )
            if between:
                a_val = float(between.group(1))
                b_val = float(between.group(2))
                if expect_error and (
                    bool(re.search(r"\bnot\s+between\b", low))
                    or "must be between" in low
                    or "outside" in low
                ):
                    delta = _smart_delta(a_val, is_float, low_name)
                    res_val = a_val - delta
                    explicitly_mutated_for_error = True
                else:
                    res_val = round((a_val + b_val) / 2.0, 2)
                inputs[name] = float(res_val) if is_float or "." in between.group(1) or "." in between.group(2) else int(round(res_val))
                continue

            # D) Comparisons (symbolic or natural English phrases)
            comp_pre = re.search(
                rf"\b(?:{alias_pat}|value)\b(?:\s+(?:is|of|are|was|must\s+be|at))?\s*(>=|<=|>|<|==|!=|at\s+or\s+below|at\s+or\s+above|at\s+most|at\s+least|no\s+more\s+than|no\s+less\s+than|less\s+than\s+or\s+equal\s+to|greater\s+than\s+or\s+equal\s+to|below|under|less\s+than|lower\s+than|fewer\s+than|above|over|greater\s+than|more\s+than|higher\s+than|exceeds?|up\s+to)\s*(-?\d+(?:\.\d+)?)\b",
                cond,
                re.IGNORECASE,
            )
            comp_post = None if comp_pre else re.search(
                rf"\b(?:{alias_pat}|value)\b(?:\s+(?:is|of|are|was|=|==|:))?\s*(-?\d+(?:\.\d+)?)\s+(or\s+higher|or\s+above|or\s+more|or\s+greater|\+|or\s+lower|or\s+below|or\s+less)\b",
                cond,
                re.IGNORECASE,
            )

            if comp_pre or comp_post:
                if comp_pre:
                    op = _op_from_phrase(comp_pre.group(1))
                    num_str = comp_pre.group(2)
                else:
                    assert comp_post is not None
                    num_str = comp_post.group(1)
                    op = _op_from_phrase(comp_post.group(2))

                thresh = float(num_str) if is_float or "." in num_str else int(num_str)
                delta = _smart_delta(float(thresh), is_float, low_name)

                if op in {">=", "<=", "=="}:
                    val_res = thresh
                elif op == ">":
                    val_res = thresh + delta
                    if is_gpa and not expect_error:
                        val_res = min(4.0, round(val_res, 2))
                elif op == "<":
                    val_res = thresh - delta
                    if thresh > 0 and not expect_error:
                        floor = 0.0 if is_float else 0
                        if val_res < floor:
                            val_res = round(thresh / 2.0, 2) if is_float else max(0, int(thresh) - 1)
                elif op == "!=":
                    val_res = thresh + delta
                else:
                    val_res = thresh

                if (op in {"<", "<="} and float(thresh) <= 0) or (expect_error and (op in {">", "<"})):
                    explicitly_mutated_for_error = True
                inputs[name] = float(val_res) if is_float else int(round(val_res))
            else:
                # E) Direct equality: "name is 500", "name = 500", "name of 100"
                direct = re.search(
                    rf"\b(?:{alias_pat})\s*(?:is|=|==|:|of|to|was)\s*(-?\d+(?:\.\d+)?)\b",
                    cond,
                    re.IGNORECASE,
                )
                if direct:
                    inputs[name] = (
                        float(direct.group(1))
                        if is_float or "." in direct.group(1)
                        else int(direct.group(1))
                    )

            # F) Modulo constraint: name % 100 == 0
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
            str_match = re.search(rf"\b(?:{alias_pat})\s*(?:is|=|==|:|of)?\s*['\"]([^'\"]+)['\"]", cond, re.IGNORECASE)
            if str_match:
                inputs[name] = str_match.group(1)
            elif re.search(rf"\b{re.escape(name)}\s*(?:is|=|==)?\s*SAVE10\b", cond, re.IGNORECASE) or ("save10" in low and "coupon" in low_name):
                inputs[name] = "SAVE10"
            elif (
                "no coupon" in low
                or "without coupon" in low
                or "coupon is none" in low
                or "none" in low
            ) and "coupon" in low_name:
                inputs[name] = None
            elif ("empty" in low or re.search(rf"\bnot\s+(?:{alias_pat})\b", low)) and (
                low_name in low or "string" in low or expect_error
            ):
                inputs[name] = ""
                explicitly_mutated_for_error = True

    # 2. Derived score-list mapping when condition specifies GPA tiers/labels for a scores function
    if "gpa" not in {p.get("name", "").lower() for p in params}:
        score_list_param = next(
            (
                p.get("name")
                for p in params
                if p.get("name", "").lower() in {"scores", "marks", "grades"}
                and isinstance(inputs.get(p.get("name")), list)
                and len(inputs[p.get("name")]) > 0
            ),
            None,
        )
        if score_list_param and ("gpa" in low or "dean" in low or "probation" in low or "good standing" in low):
            primary_low = re.split(r";|\botherwise\b", low, maxsplit=1)[0]
            if "probation" in primary_low or re.search(r"(?:gpa\s*<\s*2|below\s+2\.0)", primary_low):
                inputs[score_list_param] = [30.0, 40.0]
            elif "dean" in primary_low or re.search(r"gpa\s*(?:>=|of)\s*3\.[789]", primary_low):
                inputs[score_list_param] = [95.0, 98.0]
            elif "between 2.0" in primary_low or "good standing" in primary_low or re.search(r"gpa\s*>=\s*2\.0", primary_low):
                inputs[score_list_param] = [65.0, 75.0]

    # 3. Guarantee error tests never run on safe defaults if clear invalid keywords were missed
    if expect_error and not explicitly_mutated_for_error:
        for p in params:
            pname = p.get("name")
            if not pname or pname not in inputs:
                continue
            pval = inputs[pname]
            panno = str(p.get("annotation") or "").lower()
            is_num = isinstance(pval, (int, float)) and not isinstance(pval, bool)
            if "empty" in low and (isinstance(pval, list) or "list" in panno):
                inputs[pname] = []
                explicitly_mutated_for_error = True
                break
            if is_num and ("negative" in low or "below 0" in low or "< 0" in low):
                inputs[pname] = -10.0 if isinstance(pval, float) else -10
                explicitly_mutated_for_error = True
                break
            if is_num and ("above 100" in low or "> 100" in low):
                inputs[pname] = 105.0 if isinstance(pval, float) else 105
                explicitly_mutated_for_error = True
                break

    # 4. Relational constraints between any pairs of numeric parameters: pA >= pB, pA < pB
    num_params = [p["name"] for p in params if isinstance(inputs.get(p.get("name")), (int, float)) and not isinstance(inputs.get(p.get("name")), bool)]
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


def _build_ast_hints(source_code: str) -> dict[str, dict[str, Any]]:
    """Statically inspect AST literals, variable names, and raises per function (never executes code)."""
    hints: dict[str, dict[str, Any]] = {}
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return hints

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        str_literals: list[str] = []
        num_literals: set[str] = set()
        var_names: set[str] = set()
        has_raise = False
        for inner in ast.walk(node):
            if isinstance(inner, ast.Raise):
                has_raise = True
            elif isinstance(inner, ast.Name):
                var_names.add(inner.id.lower())
            elif isinstance(inner, ast.Constant):
                if isinstance(inner.value, str) and len(inner.value.strip()) >= 3:
                    str_literals.append(inner.value.strip().lower())
                elif isinstance(inner.value, (int, float)) and not isinstance(inner.value, bool):
                    num_literals.add(str(inner.value))
                    if isinstance(inner.value, float) and inner.value.is_integer():
                        num_literals.add(str(int(inner.value)))
        hints[node.name] = {
            "str_literals": str_literals,
            "num_literals": num_literals,
            "var_names": var_names,
            "has_raise": has_raise,
        }
    return hints


def _pick_function_for_requirement(
    requirement: dict[str, str],
    catalog: list[dict[str, Any]],
    index: int,
    ast_hints: dict[str, dict[str, Any]] | None = None,
) -> str | None:
    if not catalog:
        return None
    blob = f"{requirement.get('condition', '')} {requirement.get('expected_result', '')}".lower()
    req_expects_list = "list" in blob or "empty" in blob
    req_expects_error = any(w in blob for w in ("valueerror", "raise", "exception", "reject", "invalid"))

    scored: list[tuple[int, str]] = []
    for entry in catalog:
        raw_name = entry["name"]
        name = raw_name.lower()
        spaced_name = name.replace("_", " ")
        score = 0

        # 1. Exact whole-word function name match
        if re.search(rf"\b{re.escape(name)}\b", blob) or re.search(rf"\b{re.escape(spaced_name)}\b", blob):
            score += 100
        else:
            name_parts = [p for p in name.split("_") if len(p) > 2]
            for part in name_parts:
                if re.search(rf"\b{re.escape(part)}\b", blob):
                    score += 20

        # 2. Parameter name & type matching (whole-word only, normalized underscores)
        has_list_param = False
        for p in entry.get("params") or []:
            pname = str(p.get("name") or "").lower()
            panno = str(p.get("annotation") or "").lower()
            if not pname or pname in {"self", "cls"}:
                continue
            if "list" in panno or "array" in panno or pname in {"prices", "scores", "items", "numbers"}:
                has_list_param = True

            pspacing = pname.replace("_", " ")
            if re.search(rf"\b{re.escape(pname)}\b", blob) or re.search(rf"\b{re.escape(pspacing)}\b", blob):
                score += 25
            elif pname in {"price", "unit_price"} and re.search(r"\b(?:price|unit price)\b", blob):
                score += 25
            elif pname in {"quantity", "qty"} and re.search(r"\b(?:quantity|qty)\b", blob):
                score += 25
            elif pname == "score" and not req_expects_list and re.search(r"\bscores?\b", blob):
                score += 25
            elif pname in {"scores"} and re.search(r"\b(?:scores|score list)\b", blob):
                score += 25
            elif pname in {"prices"} and re.search(r"\b(?:prices|price list|checkout)\b", blob):
                score += 25
            elif pname == "family_income" and re.search(r"\b(?:family income|income)\b", blob):
                score += 25

        if req_expects_list and has_list_param:
            score += 35

        # 3. Domain keyword synergy
        if "discount" in name and "discount" in blob:
            score += 20
        if "shipping" in name and "shipping" in blob:
            score += 30
        if "quantity" in name and "quantity" in blob:
            score += 20
        if "checkout" in name and ("checkout" in blob or "cart" in blob):
            score += 20
        if "scholarship" in name and "scholarship" in blob:
            score += 25
        if "gpa" in name and "gpa" in blob:
            score += 25

        # 4. Static AST hints (literals, constants, local variables, raises)
        hint = (ast_hints or {}).get(raw_name)
        if hint:
            if req_expects_error and hint["has_raise"]:
                score += 15
            for lit in hint["str_literals"]:
                if " " in lit and lit in blob:
                    score += 60
                elif " " in lit:
                    lit_words = [w for w in re.split(r"[^a-z0-9]+", lit) if len(w) >= 4 and w not in {"must", "cannot", "between"}]
                    if lit_words and sum(1 for w in lit_words if re.search(rf"\b{re.escape(w)}\b", blob)) >= 2:
                        score += 25
            for vname in hint["var_names"]:
                if len(vname) >= 3 and re.search(rf"\b{re.escape(vname)}\b", blob):
                    score += 10
            num_hits = 0
            for nstr in hint["num_literals"]:
                if len(nstr) >= 2 and nstr not in {"10"} and re.search(rf"(?<!\d){re.escape(nstr)}(?!\d)", blob):
                    num_hits += 1
            score += min(num_hits, 3) * 15

        scored.append((score, raw_name))

    scored.sort(key=lambda x: x[0], reverse=True)
    if scored and scored[0][0] > 0:
        return scored[0][1]

    return catalog[index % len(catalog)]["name"]


_NEGATED_ERROR_RE = re.compile(
    r"\b(?:no|without|not|never|doesn't|does not|do not|must not|should not)"
    r"\s+(?:uncaught\s+)?(?:errors?|exceptions?|raise[sd]?|valueerror)\b",
    re.IGNORECASE,
)


def description_implies_exception(text: str) -> str | None:
    """Return 'ValueError' only when text genuinely predicts an error/exception (ignoring negations like 'no error')."""
    if not text:
        return None
    cleaned = _NEGATED_ERROR_RE.sub(" ", str(text).lower())
    if re.search(r"\b(?:valueerror|exceptions?|raises?|errors?)\b", cleaned):
        return "ValueError"
    return None


def sanitize_inputs_for_params(inputs: dict[str, Any], params: list[dict[str, Any]]) -> dict[str, Any]:
    """Normalize parameter names, backfill missing parameters, and coerce collection types safely."""
    expected_params = [p["name"] for p in params if p.get("name")]
    if not expected_params:
        return dict(inputs) if isinstance(inputs, dict) else {}
    raw_inputs = dict(inputs) if isinstance(inputs, dict) else {}
    param_obj_by_name = {p["name"]: p for p in params if p.get("name")}
    valid_keys = [k for k in raw_inputs.keys() if k in expected_params]
    if not valid_keys and raw_inputs:
        vals = list(raw_inputs.values())
        sanitized = {
            p_name: vals[i] if i < len(vals) else _infer_domain_default(
                p_name,
                str(param_obj_by_name.get(p_name, {}).get("annotation") or ""),
                param_obj_by_name.get(p_name, {}).get("default"),
            )
            for i, p_name in enumerate(expected_params)
        }
    else:
        sanitized = {k: v for k, v in raw_inputs.items() if k in expected_params}
        for p_name in expected_params:
            if p_name not in sanitized:
                p_meta = param_obj_by_name.get(p_name, {})
                sanitized[p_name] = _infer_domain_default(
                    p_name,
                    str(p_meta.get("annotation") or ""),
                    p_meta.get("default"),
                )

    for p_name in expected_params:
        p_meta = param_obj_by_name.get(p_name, {})
        p_anno = str(p_meta.get("annotation") or "").lower()
        if (
            "list" in p_anno
            or "array" in p_anno
            or p_name.lower() in {"prices", "scores", "grades", "marks", "items", "numbers", "values", "cart"}
        ) and not isinstance(sanitized.get(p_name), list):
            if sanitized.get(p_name) is None:
                sanitized[p_name] = []
            elif isinstance(sanitized.get(p_name), (int, float, str)):
                sanitized[p_name] = [sanitized.get(p_name)]
            else:
                sanitized[p_name] = _infer_domain_default(p_name, p_anno, p_meta.get("default"))
    return sanitized


def match_requirement_id(
    function_name: str,
    description: str,
    expected_exception: str | None,
    structured_requirements: list[dict[str, str]],
) -> str:
    """Semantically map a test case to its most relevant requirement ID instead of round-robin modulo."""
    if not structured_requirements:
        return "REQ-01"
    fn_low = str(function_name or "").lower()
    fn_spaced = fn_low.replace("_", " ")
    desc_low = str(description or "").lower()
    desc_tokens = {tok for tok in re.findall(r"[a-z0-9_.]+", desc_low) if len(tok) >= 2}
    case_is_error = bool(expected_exception)

    best_score = -10**9
    best_id = str(structured_requirements[0].get("requirement_id") or "REQ-01")
    for req in structured_requirements:
        rid = str(req.get("requirement_id") or "").strip()
        if not rid:
            continue
        blob = f"{req.get('condition', '')} {req.get('expected_result', '')}".lower()
        score = 0
        if fn_low and (re.search(rf"\b{re.escape(fn_low)}\b", blob) or re.search(rf"\b{re.escape(fn_spaced)}\b", blob)):
            score += 100
        elif fn_low:
            for part in fn_low.split("_"):
                if len(part) > 2 and re.search(rf"\b{re.escape(part)}\b", blob):
                    score += 20

        req_is_error = bool(description_implies_exception(blob)) or (
            ("reject" in blob or "invalid" in blob or "<= 0" in blob or "< 0" in blob)
            and "return" not in blob
        )
        if req_is_error == case_is_error:
            score += 40
        else:
            score -= 50

        for tok in desc_tokens:
            if tok in blob:
                score += 10

        if score > best_score:
            best_score = score
            best_id = rid
    return best_id


def _find_callee_call_for_field(
    tree: ast.AST,
    caller_name: str,
    target_field: str,
) -> tuple[str, list[str]] | None:
    """Find a helper call inside `caller_name` whose result feeds `target_field` in the returned dict."""
    fn_node = next(
        (n for n in getattr(tree, "body", []) if isinstance(n, ast.FunctionDef) and n.name == caller_name),
        None,
    )
    if fn_node is None:
        return None
    defined_fns = {n.name for n in getattr(tree, "body", []) if isinstance(n, ast.FunctionDef)}

    assigned_calls: dict[str, tuple[str, list[str]]] = {}
    for stmt in ast.walk(fn_node):
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            val = stmt.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id in defined_fns:
                args = [a.id for a in val.args if isinstance(a, ast.Name)]
                assigned_calls[stmt.targets[0].id] = (val.func.id, args)

    for stmt in ast.walk(fn_node):
        if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Dict):
            for key_node, val_node in zip(stmt.value.keys, stmt.value.values):
                if (
                    isinstance(key_node, ast.Constant)
                    and isinstance(key_node.value, str)
                    and key_node.value.lower() == target_field.lower()
                ):
                    if isinstance(val_node, ast.Name) and val_node.id in assigned_calls:
                        return assigned_calls[val_node.id]
                    if (
                        isinstance(val_node, ast.Call)
                        and isinstance(val_node.func, ast.Name)
                        and val_node.func.id in defined_fns
                    ):
                        return val_node.func.id, [a.id for a in val_node.args if isinstance(a, ast.Name)]

    if len(assigned_calls) == 1:
        return next(iter(assigned_calls.values()))
    return None


def _normalize_cases(
    data: Any,
    requirement_ids: set[str],
    allowed_functions: set[str],
    public_api: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    func_param_map = {
        entry["name"]: entry.get("params") or []
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
                    cond = str(req.get("condition") or "")
                    exc = description_implies_exception(cond)
                    items.append({
                        "case_id": f"bb{r_idx}",
                        "description": cond or f"Requirement {req.get('requirement_id')}",
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

        # Sanitize parameter names, backfill missing params, and enforce collection types
        expected_param_objs = func_param_map.get(function_name, [])
        inputs = sanitize_inputs_for_params(inputs, expected_param_objs)

        expected_output = item.get("expected_output")
        expected_exception = item.get("expected_exception")
        desc = str(item.get("description") or f"Black-box case {index}").strip()

        if expected_exception is None and "expected_output" not in item:
            if description_implies_exception(desc):
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

        entry_out: dict[str, Any] = {
            "case_id": str(item.get("case_id") or f"bb{index}"),
            "description": desc,
            "requirement_id": req_id,
            "function_name": function_name,
            "input": inputs,
            "expected_output": expected_output,
            "expected_exception": str(expected_exception).strip() if expected_exception else None,
            "test_type": "black_box",
        }
        for extra_k in ("expected_field", "expected_field_value", "expected_callee", "expected_callee_args", "expected_delta", "assert_output"):
            if extra_k in item:
                entry_out[extra_k] = item[extra_k]
        normalized.append(entry_out)

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
    except (json.JSONDecodeError, BlackBoxError, TypeError, ValueError) as exc:
        if isinstance(exc, BlackBoxError) and isinstance(exc.__cause__, LLMError):
            raise
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
    name_to_ret = {entry["name"]: str(entry.get("return_type") or "").lower() for entry in public_api}
    ast_hints = _build_ast_hints(source_code)
    cases: list[dict[str, Any]] = []

    for index, requirement in enumerate(structured_requirements):
        function_name = _pick_function_for_requirement(
            requirement, public_api, index, ast_hints=ast_hints
        )
        if not function_name or function_name not in defined_functions:
            continue
        params = name_to_params.get(function_name, [])
        ret_type = name_to_ret.get(function_name, "")
        condition_text = str(requirement.get("condition") or "")
        expected_text = str(requirement.get("expected_result") or "")
        combined_text = f"{condition_text} {expected_text}".strip()
        condition_lower = condition_text.lower()
        combined_lower = combined_text.lower()

        expected_exception = description_implies_exception(combined_text)
        if not expected_exception and "return" not in combined_lower:
            if (
                "reject" in combined_lower
                or "invalid" in combined_lower
                or "<= 0" in condition_lower
                or "< 0" in condition_lower
            ):
                expected_exception = "ValueError"

        inputs = _inputs_from_condition(
            condition_text, params, expect_error=bool(expected_exception)
        )

        if expected_exception:
            cases.append(
                {
                    "case_id": f"bb-req-{index + 1}",
                    "description": condition_text,
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

        # 1. Additive bonus / fee adjustment on dict fields (e.g. "add a 500.0 honor bonus to scholarship when ...")
        bonus_match = re.search(
            r"\b(?:add|include|apply|grant)\s+(?:an?\s+)?\$?(\d+(?:\.\d+)?)\b[^.;\n]*?\b(?:bonus|fee|surcharge|reward|credit|stipend|premium)\b[^.;\n]*?\bto\s+(\w+)",
            combined_lower,
        )
        if bonus_match:
            delta_val = float(bonus_match.group(1))
            target_field = bonus_match.group(2)
            callee_info = _find_callee_call_for_field(tree, function_name, target_field)
            if callee_info:
                callee_name, callee_args = callee_info
                cases.append(
                    {
                        "case_id": f"bb-req-{index + 1}",
                        "description": condition_text,
                        "requirement_id": requirement["requirement_id"],
                        "function_name": function_name,
                        "input": inputs,
                        "expected_output": None,
                        "expected_exception": None,
                        "expected_field": target_field,
                        "expected_callee": callee_name,
                        "expected_callee_args": callee_args,
                        "expected_delta": delta_val,
                        "test_type": "black_box",
                        "source": "heuristic-fallback",
                        "assert_output": True,
                    }
                )
                continue

        # 2. Dict field assignment (e.g. "assigns status Dean's List when gpa >= 3.7")
        field_match = re.search(
            r"\b(?:assigns?|sets?|marks?)\s+(\w+)\s+(?:to\s+|as\s+|=\s*)?([\"']?)([A-Za-z0-9_' -]+?)\2(?=\s+(?:when|if|unless)\b|\s*;\s*otherwise\b|[.;,]|$)",
            combined_text,
            re.IGNORECASE,
        )
        if field_match and ret_type in {"dict", ""}:
            target_field = field_match.group(1).strip()
            field_val = field_match.group(3).strip().strip("\"'")
            if field_val:
                cases.append(
                    {
                        "case_id": f"bb-req-{index + 1}",
                        "description": condition_text,
                        "requirement_id": requirement["requirement_id"],
                        "function_name": function_name,
                        "input": inputs,
                        "expected_output": None,
                        "expected_exception": None,
                        "expected_field": target_field,
                        "expected_field_value": field_val,
                        "test_type": "black_box",
                        "source": "heuristic-fallback",
                        "assert_output": True,
                    }
                )
                otherwise_match = re.search(
                    r";\s*otherwise\s+(?:assigns?\s+\w+\s+(?:to\s+)?)?([\"']?)([A-Za-z0-9_' -]+?)\1(?=[.;,]|$)",
                    combined_text,
                    re.IGNORECASE,
                )
                score_list_param = next(
                    (
                        p.get("name")
                        for p in params
                        if str(p.get("name") or "").lower() in {"scores", "marks", "grades"}
                    ),
                    None,
                )
                if otherwise_match and score_list_param:
                    alt_val = otherwise_match.group(2).strip().strip("\"'")
                    low_inputs = dict(inputs)
                    low_inputs[score_list_param] = [30.0, 40.0]
                    cases.append(
                        {
                            "case_id": f"bb-req-{index + 1}-else",
                            "description": f"{condition_text} (otherwise fallback)",
                            "requirement_id": requirement["requirement_id"],
                            "function_name": function_name,
                            "input": low_inputs,
                            "expected_output": None,
                            "expected_exception": None,
                            "expected_field": target_field,
                            "expected_field_value": alt_val,
                            "test_type": "black_box",
                            "source": "heuristic-fallback",
                            "assert_output": True,
                        }
                    )
                continue

        # 3. Exact boolean return expectations ("returns True", "returns False")
        bool_match = re.search(
            r"\b(?:returns?|must\s+return|evaluates?\s+to)\s+(true|false)\b",
            combined_lower,
        )
        if bool_match and not re.search(r"\bnot\s+(?:returns?|must\s+return)\b", combined_lower):
            cases.append(
                {
                    "case_id": f"bb-req-{index + 1}",
                    "description": condition_text,
                    "requirement_id": requirement["requirement_id"],
                    "function_name": function_name,
                    "input": inputs,
                    "expected_output": bool_match.group(1) == "true",
                    "expected_exception": None,
                    "test_type": "black_box",
                    "source": "heuristic-fallback",
                    "assert_output": True,
                }
            )
            continue

        # 4. Safely detect explicit exact scalar return values (e.g. "returns 5000.0 when ...")
        expected_output = None
        assert_output = False
        if ret_type not in {"dict", "str", "list", "bool"} and not any(
            word in combined_lower for word in ("scale", "decimal", "percent", "%", "discount", "off", "bonus")
        ):
            ret_match = re.search(
                r"\b(?:returns?|must\s+return|produce(?:s)?(?:\s+a\s+[\w\s]+)?\s+of\s+(?:exactly\s+)?)\s*(-?\d+(?:\.\d+)?)\b",
                combined_lower,
            )
            if ret_match:
                num_s = ret_match.group(1)
                expected_output = float(num_s) if ("float" in ret_type or "." in num_s) else int(num_s)
                assert_output = True

        cases.append(
            {
                "case_id": f"bb-req-{index + 1}",
                "description": condition_text,
                "requirement_id": requirement["requirement_id"],
                "function_name": function_name,
                "input": inputs,
                "expected_output": expected_output,
                "expected_exception": None,
                "test_type": "black_box",
                "source": "heuristic-fallback",
                "assert_output": assert_output,
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
        lines.extend(case_assertion_lines(case, call))
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
        import config as _cfg

        key = NVIDIA_API_KEY.strip()
        key_overridden = bool(key) and key != (_cfg.NVIDIA_API_KEY or "").strip()
        if (bool(key) and (key_overridden or not is_nvidia_exhausted())) or llm_is_configured():
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
