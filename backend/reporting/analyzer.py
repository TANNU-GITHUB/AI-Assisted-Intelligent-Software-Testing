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
            }

    return {}


def build_report_data(payload: dict) -> dict:
    execution = payload.get("test_execution") or {}
    coverage = payload.get("coverage") or {}
    tests = execution.get("tests") or []
    requirements = (payload.get("requirement_analysis") or {}).get("requirements") or []
    traceability = []

    for requirement in requirements:
        requirement_id = requirement.get("requirement_id")
        linked_tests = [test for test in tests if test.get("requirement_id") == requirement_id]
        traceability.append(
            {
                "requirement_id": requirement_id,
                "description": requirement.get("condition") or requirement.get("expected_result") or "",
                "tests": linked_tests,
                "failed": any(test.get("status") in {"failed", "error"} for test in linked_tests),
                "flaky": any(test.get("flaky") for test in linked_tests),
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

    return {
        "session_id": payload.get("session_id", "unknown"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "summary": {
            "total": execution.get("total", len(tests)),
            "passed": execution.get("passed", 0),
            "failed": execution.get("failed", 0),
            "errors": execution.get("errors", 0),
            "flaky": execution.get("flaky", sum(bool(test.get("flaky")) for test in tests)),
        },
        "coverage_percent": coverage.get("overall_line_coverage_percent"),
        "requirement_coverage": payload.get("requirement_coverage") or {},
        "missing_lines": coverage.get("missing_lines") or [],
        "source_lines": coverage.get("source_lines") or [],
        "requirements": requirements,
        "traceability": traceability,
        "function_coverage": functions,
        "coverage_warnings": warnings,
        "coverage_note": coverage.get("function_coverage_note"),
        "defects": [
            {
                **test,
                **_parse_error_details(test.get("error_message") or ""),
                **_find_test_case_inputs(test.get("test_id") or "", payload),
            }
            for test in tests
            if test.get("status") in {"failed", "error"} and not test.get("flaky")
        ],
        "passed_tests": [
            {
                **test,
                **_find_test_case_inputs(test.get("test_id") or "", payload),
            }
            for test in tests
            if test.get("status") == "passed" and not test.get("flaky")
        ],
    }


def render_session_report(session_id: str) -> str:
    payload = load_session(session_id)
    template = _TEMPLATES.get_template("report.html")
    return template.render(**build_report_data(payload))