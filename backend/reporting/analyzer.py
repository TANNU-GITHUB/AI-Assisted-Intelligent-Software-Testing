from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from input_handler.handler import load_session


_TEMPLATE_DIR = Path(__file__).parent
_TEMPLATES = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def _parse_error_details(error_message: str) -> dict:
    """Extract exception type, value, and failing call line from pytest longrepr."""
    if not error_message:
        return {}

    # Match lines like: "E   ValueError: -10"  or  "E   AssertionError: assert -10 == 5"
    exc_match = re.search(
        r"E\s+([\w]+(?:Error|Exception|Warning|Stop|Exit)?)\s*:\s*(.+)",
        error_message,
    )
    exc_type = exc_match.group(1) if exc_match else None
    exc_value = exc_match.group(2).strip() if exc_match else None

    # Match the failing source line: ">   result = func(...)"
    call_match = re.search(r">\s+(.+)", error_message)
    failing_line = call_match.group(1).strip() if call_match else None

    return {
        "exception_type": exc_type,
        "exception_value": exc_value,
        "failing_line": failing_line,
    }


def _find_test_case_inputs(test_id: str, payload: dict) -> dict:
    """Match a test_id node-id back to its generated test-case to retrieve input values."""
    if not test_id:
        return {}

    # Determine which bucket to search
    tid = test_id.lower()
    cases = []
    if "white_box" in tid:
        wb = payload.get("white_box_tests") or {}
        functions = wb.get("functions") or []
        for fn in functions:
            fn_name = (fn.get("function") or "").lower()
            if fn_name and fn_name in tid:
                cases = fn.get("cases") or []
                break
        if not cases:
            raw = wb.get("test_cases")
            cases = raw if isinstance(raw, list) else []
    elif "black_box" in tid:
        raw = (payload.get("black_box_tests") or {}).get("test_cases")
        cases = raw if isinstance(raw, list) else []
    elif "gray_box" in tid:
        raw = (payload.get("gray_box_tests") or {}).get("test_cases")
        cases = raw if isinstance(raw, list) else []
    elif "integration" in tid:
        raw = (payload.get("other_tests") or {}).get("integration_tests")
        cases = raw if isinstance(raw, list) else []
    elif "negative" in tid:
        raw = (payload.get("other_tests") or {}).get("negative_tests")
        cases = raw if isinstance(raw, list) else []
    elif "gap_fill" in tid:
        raw = (payload.get("gap_fill") or {}).get("test_cases")
        cases = raw if isinstance(raw, list) else []
        if not cases:
            sid = payload.get("session_id")
            if sid:
                from config import SESSIONS_DIR

                gap_py = SESSIONS_DIR / sid / "tests" / "gap_fill" / "test_gap_fill.py"
                if gap_py.is_file():
                    try:
                        content = gap_py.read_text(encoding="utf-8")
                        for match in re.finditer(
                            r"def\s+(test_gap_case_\d+).*?json\.loads\('([^']+)'\)", content, re.DOTALL
                        ):
                            cases.append({"case_id": match.group(1), "input": json.loads(match.group(2))})
                    except Exception:
                        pass
    else:
        cases = []

    if not isinstance(cases, list):
        cases = []

    # Extract 1-based case number from the node id, e.g. "case3" → 3
    case_num_match = re.search(r"case_?(\d+)", test_id, re.IGNORECASE)
    if case_num_match:
        idx = int(case_num_match.group(1)) - 1
        if 0 <= idx < len(cases):
            tc = cases[idx]
            if isinstance(tc, dict):
                return {
                    "function_name": tc.get("function_name") or tc.get("caller") or "",
                    "input_values": tc.get("input") or {},
                    "expected_output": tc.get("expected_output"),
                    "expected_exception": tc.get("expected_exception"),
                    "requirement_id": tc.get("requirement_id"),
                    "description": tc.get("description") or tc.get("target_branch") or "",
                }

    # Fallback: match by case_id field
    for tc in cases:
        if not isinstance(tc, dict):
            continue
        cid = str(tc.get("case_id") or "")
        if cid and cid in test_id:
            return {
                "function_name": tc.get("function_name") or tc.get("caller") or "",
                "input_values": tc.get("input") or {},
                "expected_output": tc.get("expected_output"),
                "expected_exception": tc.get("expected_exception"),
                "requirement_id": tc.get("requirement_id"),
                "description": tc.get("description") or tc.get("target_branch") or "",
            }

    return {}


def _determine_test_category(test_id: str) -> str:
    tid = test_id.lower()
    if "white_box" in tid:
        return "White-Box"
    if "black_box" in tid:
        return "Black-Box"
    if "gray_box" in tid:
        return "Gray-Box"
    if "integration" in tid:
        return "Integration"
    if "negative" in tid:
        return "Negative"
    if "gap" in tid:
        return "Gap-Fill"
    return "Unit Test"


def _clean_test_name(test_id: str) -> str:
    """Format node ID into a clean, human-readable test name."""
    if not test_id:
        return "Test Case"
    tid = test_id.lower()

    case_num_match = re.search(r"case_?(\d+)", test_id, re.IGNORECASE)
    case_num = f"Case {case_num_match.group(1)}" if case_num_match else "Test"

    req_match = re.search(r"\[(REQ[-_]\d+)\]", test_id, re.IGNORECASE) or re.search(r"_(REQ[-_]\d+)", test_id, re.IGNORECASE)
    req_tag = f" ({req_match.group(1).replace('_', '-').upper()})" if req_match else ""

    if "black_box" in tid:
        return f"Black-Box {case_num}{req_tag}"
    if "gray_box" in tid:
        return f"Gray-Box {case_num}{req_tag}"
    if "white_box" in tid:
        return f"White-Box Branch {case_num_match.group(1) if case_num_match else '1'}"
    if "integration" in tid:
        return f"Integration Scenario {case_num_match.group(1) if case_num_match else '1'}"
    if "negative" in tid:
        return f"Negative Boundary {case_num_match.group(1) if case_num_match else '1'}"
    if "gap" in tid:
        return f"Gap-Fill Case {case_num_match.group(1) if case_num_match else '1'}"

    parts = test_id.split("::")
    raw = parts[-1]
    raw = re.sub(r"\[.*?\]", "", raw)
    return raw.replace("_", " ").strip().title()


def _format_expected(test: dict, test_inputs: dict) -> str:
    expected_exc = test_inputs.get("expected_exception") or test.get("expected_exception")
    if expected_exc:
        return f"Raise {expected_exc}"
    expected_out = test_inputs.get("expected_output") if test_inputs.get("expected_output") is not None else test.get("expected_output")
    if expected_out is not None:
        if isinstance(expected_out, (dict, list)):
            return f"Return {json.dumps(expected_out)}"
        return f"Return {expected_out}"
    if test.get("requirement_expected"):
        return str(test.get("requirement_expected"))
    return "Valid execution (no uncaught error)"


def _format_actual(test: dict, test_inputs: dict, err_details: dict) -> str:
    status = test.get("status")
    if status == "passed":
        expected_exc = test_inputs.get("expected_exception") or test.get("expected_exception")
        if expected_exc:
            return f"Raised {expected_exc} as expected"
        expected_out = test_inputs.get("expected_output") if test_inputs.get("expected_output") is not None else test.get("expected_output")
        if expected_out is not None:
            return f"Returned {expected_out} (Matches expected)"
        return "Executed successfully without errors"
    if status == "skipped":
        return "Test was skipped"

    why = test.get("why_failed")
    if why:
        return why

    exc_type = err_details.get("exception_type")
    exc_val = err_details.get("exception_value")
    if exc_type and exc_val:
        return f"{exc_type}: {exc_val}"
    if exc_type:
        return f"{exc_type} raised unexpectedly"

    err = (test.get("error_message") or "").strip()
    if err:
        m = re.search(r"AssertionError:\s*assert\s+(.*?)\s+==\s+(.*)", err)
        if m:
            return f"Returned {m.group(1).strip()} (Expected {m.group(2).strip()})"
        lines = [line.lstrip("E ").strip() for line in err.splitlines() if line.strip()]
        if lines:
            return lines[-1][:140]
    return "Test failed assertion or crashed"


def _format_input_values(inputs: dict) -> str:
    if not inputs:
        return "—"
    items = []
    for k, v in inputs.items():
        if isinstance(v, str):
            val_str = f"'{v}'"
        else:
            val_str = str(v)
        items.append(f"{k}={val_str}")
    return ", ".join(items)


def build_report_data(payload: dict) -> dict:
    execution = payload.get("test_execution") or {}
    coverage = payload.get("coverage") or {}
    tests = execution.get("tests") or []
    requirements = (payload.get("requirement_analysis") or {}).get("requirements") or []
    code_functions = (payload.get("code_analysis") or {}).get("functions") or []

    # Map each function name to its line range
    fn_map = {
        fn.get("name"): f"L{fn.get('lineno', '?')}–L{fn.get('end_lineno', '?')}"
        for fn in code_functions
        if fn.get("name")
    }

    # Enrich every test with its inputs, category, and error parsing
    all_tests = []
    for test in tests:
        tid = test.get("test_id") or ""
        test_inputs = _find_test_case_inputs(tid, payload)
        category = _determine_test_category(tid)
        err_details = _parse_error_details(test.get("error_message") or "") if test.get("status") in {"failed", "error"} else {}
        clean_name = _clean_test_name(tid)

        req_id = test.get("requirement_id") or test_inputs.get("requirement_id")
        if not req_id:
            m = re.search(r"(REQ[-_]\d+)", tid, re.IGNORECASE)
            if m:
                req_id = m.group(1).replace("_", "-").upper()

        fn_name = test_inputs.get("function_name") or test.get("function_name")
        if not fn_name:
            for cf in code_functions:
                cname = cf.get("name") or ""
                if cname and cname.lower() in tid:
                    fn_name = cname
                    break
            if not fn_name and len(code_functions) == 1:
                fn_name = code_functions[0].get("name") or ""

        expected_desc = _format_expected(test, test_inputs)
        actual_desc = _format_actual(test, test_inputs, err_details)

        enriched = {
            **test,
            **err_details,
            **test_inputs,
            "function_name": fn_name or test_inputs.get("function_name") or "",
            "requirement_id": req_id,
            "category": category,
            "clean_name": clean_name,
            "expected_desc": expected_desc,
            "actual_desc": actual_desc,
            "input_formatted": _format_input_values(test_inputs.get("input_values") or {}),
        }
        all_tests.append(enriched)

    # Build Requirement Traceability Matrix
    traceability = []
    for requirement in requirements:
        req_id = str(requirement.get("requirement_id") or "").strip()
        norm_req = req_id.replace("_", "-").upper()
        linked_tests = [
            t for t in all_tests
            if str(t.get("requirement_id") or "").replace("_", "-").upper() == norm_req
        ]

        # Determine target function from linked tests or condition text
        target_fn = "—"
        target_lines = "—"
        if linked_tests and linked_tests[0].get("function_name"):
            target_fn = linked_tests[0].get("function_name")
            target_lines = fn_map.get(target_fn, "—")
        else:
            cond = (requirement.get("condition") or "").lower()
            for fn in code_functions:
                fname = (fn.get("name") or "").lower()
                if fname in cond or fname.replace("_", " ") in cond:
                    target_fn = fn.get("name")
                    target_lines = fn_map.get(target_fn, "—")
                    break
            if target_fn == "—" and code_functions:
                target_fn = code_functions[0].get("name", "—")
                target_lines = fn_map.get(target_fn, "—")

        has_failed = any(t.get("status") in {"failed", "error"} for t in linked_tests)
        has_passed = any(t.get("status") == "passed" for t in linked_tests)
        status = "passed" if (has_passed and not has_failed) else ("failed" if has_failed else "untested")

        traceability.append(
            {
                "requirement_id": req_id,
                "condition": requirement.get("condition") or "",
                "expected_result": requirement.get("expected_result") or "",
                "description": requirement.get("condition") or requirement.get("expected_result") or "",
                "target_function": target_fn,
                "target_lines": target_lines,
                "tests": linked_tests,
                "test_count": len(linked_tests),
                "passed_count": sum(1 for t in linked_tests if t.get("status") == "passed"),
                "failed_count": sum(1 for t in linked_tests if t.get("status") in {"failed", "error"}),
                "status": status,
                "failed": has_failed,
                "flaky": any(t.get("flaky") for t in linked_tests),
            }
        )

    functions = []
    warnings = []
    for function in coverage.get("function_coverage") or []:
        branches = function.get("branches") or []
        uncovered = [branch for branch in branches if not branch.get("fully_covered")]
        functions.append(
            {
                **function,
                "covered_branch_count": len(branches) - len(uncovered),
                "zero_coverage_branches": len(uncovered),
            }
        )
        for branch in uncovered:
            warnings.append(
                f"Zero-coverage branch: {function.get('function')} at line "
                f"{branch.get('lineno')} ({branch.get('condition') or branch.get('type')})."
            )

    total_count = execution.get("total", len(tests))
    passed_count = execution.get("passed", sum(1 for t in tests if t.get("status") == "passed"))
    failed_count = execution.get("failed", sum(1 for t in tests if t.get("status") == "failed"))
    error_count = execution.get("errors", sum(1 for t in tests if t.get("status") == "error"))
    skipped_count = sum(1 for t in tests if t.get("status") == "skipped")
    flaky_count = execution.get("flaky", sum(bool(t.get("flaky")) for t in tests))

    pass_rate = round((passed_count / total_count * 100), 1) if total_count > 0 else 0.0

    # Source code retrieval for visual report display
    source_code = payload.get("source_code") or ""
    if not source_code:
        sid = payload.get("session_id")
        if sid:
            from config import SESSIONS_DIR
            src_file = SESSIONS_DIR / sid / "source.py"
            if src_file.is_file():
                try:
                    source_code = src_file.read_text(encoding="utf-8")
                except Exception:
                    pass

    return {
        "session_id": payload.get("session_id", "unknown"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "summary": {
            "total": total_count,
            "passed": passed_count,
            "failed": failed_count,
            "errors": error_count,
            "skipped": skipped_count,
            "flaky": flaky_count,
            "pass_rate": pass_rate,
        },
        "coverage_percent": coverage.get("overall_line_coverage_percent"),
        "requirement_coverage": payload.get("requirement_coverage") or {},
        "missing_lines": coverage.get("missing_lines") or [],
        "source_lines": coverage.get("source_lines") or [],
        "source_code": source_code,
        "requirements": requirements,
        "traceability": traceability,
        "function_coverage": functions,
        "coverage_warnings": warnings,
        "coverage_note": coverage.get("function_coverage_note"),
        "all_tests": all_tests,
        "defects": [t for t in all_tests if t.get("status") in {"failed", "error"} and not t.get("flaky")],
        "passed_tests": [t for t in all_tests if t.get("status") == "passed" and not t.get("flaky")],
        "skipped_tests": [t for t in all_tests if t.get("status") == "skipped"],
    }


def render_session_report(session_id: str) -> str:
    payload = load_session(session_id)
    template = _TEMPLATES.get_template("report.html")
    return template.render(**build_report_data(payload))