from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from input_handler.handler import load_session


_TEMPLATE_DIR = Path(__file__).parent
_TEMPLATES = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


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
        "requirements": requirements,
        "traceability": traceability,
        "function_coverage": functions,
        "coverage_warnings": warnings,
        "coverage_note": coverage.get("function_coverage_note"),
        "defects": [
            test
            for test in tests
            if test.get("status") in {"failed", "error"} and not test.get("flaky")
        ],
    }


def render_session_report(session_id: str) -> str:
    payload = load_session(session_id)
    template = _TEMPLATES.get_template("report.html")
    return template.render(**build_report_data(payload))