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
import os
import re
import subprocess
import sys

from input_handler.handler import load_session, save_session, session_dir
from input_handler.session_logging import log_session_error


class ExecutionError(Exception):
    """Raised when the test execution step fails."""


class CoverageError(Exception):
    """Raised when the coverage measurement step fails."""


TIMEOUT_SECONDS = 120


def _coverage_subprocess_env(folder) -> dict[str, str]:
    env = os.environ.copy()
    folder_str = str(folder)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        folder_str if not existing else f"{folder_str}{os.pathsep}{existing}"
    )
    return env


def _pytest_target_arg(folder, target) -> str:
    try:
        return str(target.relative_to(folder))
    except ValueError:
        return str(target)


def _run_coverage_for_tests(
    folder,
    pytest_target,
    coverage_json_path,
) -> tuple[bool, str]:
    """
    Run coverage.py + pytest under the session folder.
    Returns (report_written, diagnostic_snippet).
    """
    coverage_data_file = folder / ".coverage"
    coverage_data_file.unlink(missing_ok=True)
    coverage_json_path.unlink(missing_ok=True)

    env = _coverage_subprocess_env(folder)
    pytest_arg = _pytest_target_arg(folder, pytest_target)

    run_cmd = [
        sys.executable,
        "-m",
        "coverage",
        "run",
        "--branch",
        "--data-file=.coverage",
        "--source=source",
        "-m",
        "pytest",
        pytest_arg,
        "-q",
    ]
    json_cmd = [
        sys.executable,
        "-m",
        "coverage",
        "json",
        "--data-file=.coverage",
        "-o",
        "coverage.json",
    ]

    run_result = subprocess.run(
        run_cmd,
        cwd=str(folder),
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        env=env,
    )
    json_result = subprocess.run(
        json_cmd,
        cwd=str(folder),
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
        env=env,
    )

    if coverage_json_path.is_file():
        return True, ""

    chunks = [
        run_result.stderr,
        run_result.stdout,
        json_result.stderr,
        json_result.stdout,
    ]
    detail = "\n".join(part.strip() for part in chunks if part and part.strip())
    if "No module named coverage" in detail:
        detail = (
            "The Python running the API does not have coverage installed "
            f"({sys.executable}). Activate the project venv and "
            "pip install -r requirements.txt."
        )
    elif "No data to report" in detail or "no-data-collected" in detail.lower():
        detail = (
            "Tests did not import source.py (often pytest collection failed). "
            f"Pytest exit code: {run_result.returncode}. {detail}"
        )
    return False, detail[-2000:]


def _test_result(test: dict) -> dict:
    status = test.get("outcome", "error")
    error_message = next(
        (
            test.get(phase, {}).get("longrepr")
            for phase in ("call", "setup", "teardown")
            if test.get(phase, {}).get("longrepr")
        ),
        None,
    )
    node_id = test.get("nodeid")
    match = re.search(r"\[(REQ-\d+)\]", node_id or "")
    return {
        "test_id": node_id,
        "requirement_id": match.group(1) if match else None,
        "status": status,
        "duration_seconds": test.get("call", {}).get("duration"),
        "error_message": error_message if status in {"failed", "error"} else None,
    }


def _run_pytest(folder, targets: list[str], report_path) -> dict:
    report_path.unlink(missing_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *targets,
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
        raise ExecutionError("pytest not found — is it installed in this environment?") from exc

    if not report_path.is_file():
        raise ExecutionError(
            "pytest ran but produced no report — is pytest-json-report installed? "
            "(pip install pytest-json-report)"
        )
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExecutionError(f"pytest produced an invalid JSON report: {exc}") from exc


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
    try:
        first_report = _run_pytest(folder, [str(tests_dir)], report_path)
    except ExecutionError as exc:
        log_session_error(session_id, "execution", exc)
        raise
    tests = [_test_result(test) for test in first_report.get("tests", [])]
    failed_ids = [
        test["test_id"]
        for test in tests
        if test["status"] in {"failed", "error"} and test.get("test_id")
    ]

    retry_by_id = {}
    if failed_ids:
        try:
            retry_report = _run_pytest(
                folder, failed_ids, folder / "pytest_retry_report.json"
            )
        except ExecutionError as exc:
            log_session_error(session_id, "execution.retry", exc)
            raise
        retry_by_id = {
            item.get("nodeid"): _test_result(item)
            for item in retry_report.get("tests", [])
        }

    for test in tests:
        test["initial_status"] = test["status"]
        test["initial_error_message"] = test.get("error_message")
        retry = retry_by_id.get(test.get("test_id"))
        test["retry_status"] = retry.get("status") if retry else None
        test["flaky"] = bool(
            retry and test["status"] in {"failed", "error"} and retry["status"] == "passed"
        )
        if retry:
            test["status"] = retry["status"]
            test["error_message"] = retry.get("error_message")
            test["duration_seconds"] = (test.get("duration_seconds") or 0) + (
                retry.get("duration_seconds") or 0
            )

        if test["initial_status"] in {"failed", "error"}:
            log_session_error(
                session_id,
                "test_failure",
                f"{test.get('test_id')}: initial={test['initial_status']}, "
                f"retry={test.get('retry_status') or 'not run'}, "
                f"flaky={test['flaky']}; "
                f"{test.get('initial_error_message') or 'No error details reported.'}",
            )

    summary = first_report.get("summary", {})
    final_counts = {
        status: sum(1 for test in tests if test.get("status") == status)
        for status in ("passed", "failed", "error", "skipped")
    }
    result = {
        "total": len(tests) if tests else summary.get("total", 0),
        "passed": final_counts["passed"],
        "failed": final_counts["failed"],
        "errors": final_counts["error"],
        "skipped": final_counts["skipped"],
        "flaky": sum(1 for test in tests if test.get("flaky")),
        "first_run_failed": summary.get("failed", 0),
        "first_run_errors": summary.get("error", 0),
        "duration_seconds": first_report.get("duration"),
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

    source_path = folder / "source.py"
    if not source_path.is_file():
        raise FileNotFoundError(f"source.py not found for session '{session_id}'.")

    coverage_json_path = folder / "coverage.json"
    pytest_targets = [tests_dir]
    white_box_dir = tests_dir / "white_box"
    if white_box_dir.is_dir():
        pytest_targets.append(white_box_dir)

    diagnostic = ""
    try:
        for target in pytest_targets:
            ok, diagnostic = _run_coverage_for_tests(folder, target, coverage_json_path)
            if ok:
                break
    except subprocess.TimeoutExpired as exc:
        error = CoverageError(f"Coverage run timed out after {TIMEOUT_SECONDS} seconds.")
        log_session_error(session_id, "coverage", error)
        raise error from exc
    except FileNotFoundError as exc:
        error = CoverageError(
            "coverage not found — is it installed? (pip install coverage)"
        )
        log_session_error(session_id, "coverage", error)
        raise error from exc

    if not coverage_json_path.is_file():
        hint = (
            "Ensure source.py is importable as 'source' from the session folder "
            "and pytest can collect tests under sessions/<id>/tests/. "
            "If you use uvicorn --reload, exclude sessions/ from reload so test "
            "files are not rewritten mid-run."
        )
        message = f"Coverage produced no report. {hint}"
        if diagnostic:
            message = f"{message} Details: {diagnostic}"
        error = CoverageError(message)
        log_session_error(session_id, "coverage", error)
        raise error

    try:
        coverage_report = json.loads(coverage_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        error = CoverageError(f"Could not read coverage report: {exc}")
        log_session_error(session_id, "coverage", error)
        raise error from exc

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