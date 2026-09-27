"""Task 8 — Test Execution Engine, and Task 9 — Result Collection &
Coverage Analysis.

Task 8: runs whatever pytest test files exist under sessions/<id>/tests/
(from Tasks 5, 6, 7), captures pass/fail, error details, and timing.

Task 9: re-runs the same tests under coverage.py (with branch tracking),
measures line coverage per file AND per function, cross-references each
function's branches (from Task 3's code_analysis) against what coverage.py
reports as missing branches, and builds one consolidated results object
per test combining status + coverage + error message.

Requires: pip install pytest-json-report coverage
"""

from __future__ import annotations

import json
import subprocess
import sys

from input_handler.handler import load_session, save_session, session_dir


class ExecutionError(Exception):
    """Raised when the test execution step fails."""


class CoverageError(Exception):
    """Raised when the coverage measurement step fails."""


TIMEOUT_SECONDS = 60


# ---------------------------------------------------------------------------
# Task 8 — Test Execution Engine
# ---------------------------------------------------------------------------
def analyze_session_execution(session_id: str) -> dict:
    payload = load_session(session_id)
    folder = session_dir(session_id)
    tests_dir = folder / "tests"

    if not tests_dir.is_dir():
        raise FileNotFoundError(f"No tests directory found for session '{session_id}'.")

    report_path = folder / "pytest_report.json"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(tests_dir),
        "--json-report",
        f"--json-report-file={report_path}",
        "-q",
    ]

    try:
        subprocess.run(
            cmd,
            cwd=str(folder),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExecutionError(
            f"Test execution timed out after {TIMEOUT_SECONDS} seconds."
        ) from exc
    except FileNotFoundError as exc:
        raise ExecutionError(
            "pytest not found — is it installed in this environment?"
        ) from exc

    if not report_path.is_file():
        raise ExecutionError(
            "pytest ran but produced no report — is pytest-json-report installed? "
            "(pip install pytest-json-report)"
        )

    report = json.loads(report_path.read_text(encoding="utf-8"))

    tests = []
    for test in report.get("tests", []):
        tests.append(
            {
                "test_id": test.get("nodeid"),
                "status": test.get("outcome"),
                "duration_seconds": test.get("call", {}).get("duration"),
                "error_message": (
                    test.get("call", {}).get("longrepr")
                    if test.get("outcome") == "failed"
                    else None
                ),
            }
        )

    summary = report.get("summary", {})
    result = {
        "total": summary.get("total", 0),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "errors": summary.get("error", 0),
        "duration_seconds": report.get("duration"),
        "tests": tests,
    }

    payload["test_execution"] = result
    save_session(payload)
    return payload


# ---------------------------------------------------------------------------
# Task 9 — Result Collection & Coverage Analysis
# ---------------------------------------------------------------------------
def _function_coverage(code_analysis: dict, executed_lines: set[int], missing_branch_lines: set[int]) -> list[dict]:
    """
    Cross-references Task 3's function/branch map against coverage.py's
    executed lines and missing branches to build per-function coverage,
    confirming each identified branch was actually hit.
    """
    function_results = []

    for func in code_analysis.get("functions", []):
        start = func["lineno"]
        end = func.get("end_lineno", start)
        func_line_range = set(range(start, end + 1))

        covered_in_func = func_line_range & executed_lines
        line_percent = (
            round(len(covered_in_func) / len(func_line_range) * 100, 1)
            if func_line_range
            else None
        )

        branch_results = []
        for branch in func.get("branches", []):
            branch_line = branch["lineno"]
            fully_covered = branch_line not in missing_branch_lines
            branch_results.append(
                {
                    "type": branch["type"],
                    "lineno": branch_line,
                    "condition": branch.get("condition"),
                    "fully_covered": fully_covered,
                }
            )

        uncovered_branches = [b for b in branch_results if not b["fully_covered"]]

        function_results.append(
            {
                "function": func["qualified_name"],
                "line_coverage_percent": line_percent,
                "branch_count": func.get("branch_count", 0),
                "branches": branch_results,
                "has_uncovered_branch": len(uncovered_branches) > 0,
            }
        )

    return function_results


def analyze_session_coverage(session_id: str) -> dict:
    """
    Re-runs the test suite under coverage.py (with branch tracking),
    targeting source.py, and builds:
      - overall + per-file line coverage
      - per-function line + branch coverage, cross-referenced with Task 3
      - consolidated per-test results: status, coverage %, error message

    Requires analyze_session_execution() to have already populated
    payload["test_execution"] for the status/error fields.
    For per-function branch cross-referencing, run code-analysis
    (Task 3) on the session first — otherwise that section is skipped.
    """
    payload = load_session(session_id)
    folder = session_dir(session_id)
    tests_dir = folder / "tests"

    if not tests_dir.is_dir():
        raise FileNotFoundError(f"No tests directory found for session '{session_id}'.")

    coverage_json_path = folder / "coverage.json"
    coverage_data_file = folder / ".coverage"

    run_cmd = [
        sys.executable,
        "-m",
        "coverage",
        "run",
        "--branch",
        f"--data-file={coverage_data_file}",
        "--source=source",
        "-m",
        "pytest",
        str(tests_dir),
        "-q",
    ]
    json_cmd = [
        sys.executable,
        "-m",
        "coverage",
        "json",
        f"--data-file={coverage_data_file}",
        "-o",
        str(coverage_json_path),
    ]

    try:
        subprocess.run(
            run_cmd, cwd=str(folder), capture_output=True, text=True, timeout=TIMEOUT_SECONDS
        )
        subprocess.run(
            json_cmd, cwd=str(folder), capture_output=True, text=True, timeout=TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired as exc:
        raise CoverageError(f"Coverage run timed out after {TIMEOUT_SECONDS} seconds.") from exc
    except FileNotFoundError as exc:
        raise CoverageError(
            "coverage not found — is it installed? (pip install coverage)"
        ) from exc

    if not coverage_json_path.is_file():
        raise CoverageError(
            "coverage.py ran but produced no report — check that source.py "
            "is importable as 'source' from the session folder."
        )

    coverage_report = json.loads(coverage_json_path.read_text(encoding="utf-8"))

    files = coverage_report.get("files", {})
    overall = coverage_report.get("totals", {})

    per_file_summary = {}
    for filename, data in files.items():
        summary = data.get("summary", {})
        per_file_summary[filename] = {
            "line_coverage_percent": summary.get("percent_covered"),
            "covered_lines": summary.get("covered_lines"),
            "missing_lines": summary.get("missing_lines"),
            "num_statements": summary.get("num_statements"),
            "num_branches": summary.get("num_branches"),
            "covered_branches": summary.get("covered_branches"),
            "missing_branches_count": summary.get("num_partial_branches"),
        }

    overall_line_coverage = overall.get("percent_covered")

    # --- Per-function branch cross-referencing (needs Task 3 data) ---
    function_coverage: list[dict] = []
    function_coverage_note = None

    code_analysis = payload.get("code_analysis")
    source_file_data = files.get("source.py")

    if not code_analysis:
        function_coverage_note = (
            "Run code-analysis (Task 3) on this session first to get "
            "per-function branch coverage cross-referenced here."
        )
    elif not source_file_data:
        function_coverage_note = "coverage.py reported no data for source.py."
    else:
        executed_lines = set(source_file_data.get("executed_lines", []))
        missing_branches = source_file_data.get("missing_branches", [])
        missing_branch_lines = {pair[0] for pair in missing_branches}
        function_coverage = _function_coverage(
            code_analysis, executed_lines, missing_branch_lines
        )

    # --- Consolidate with test_execution results, if already run ---
    test_execution = payload.get("test_execution") or {}
    consolidated = []
    for test in test_execution.get("tests", []):
        consolidated.append(
            {
                "test_id": test.get("test_id"),
                "status": test.get("status"),
                "error_message": test.get("error_message"),
                "overall_line_coverage_percent": overall_line_coverage,
            }
        )

    result = {
        "overall_line_coverage_percent": overall_line_coverage,
        "per_file": per_file_summary,
        "function_coverage": function_coverage,
        "function_coverage_note": function_coverage_note,
        "consolidated_results": consolidated,
    }

    payload["coverage"] = result
    save_session(payload)
    return payload