"""Task 8 — Test Execution Engine, and Task 9 — Result Collection &
Coverage Analysis.

Task 8: runs whatever pytest test files exist under sessions/<id>/tests/
(from Tasks 5, 6, 7), captures pass/fail, error details, and timing.

Task 9: re-runs the same tests under coverage.py, measures line/branch
coverage, and builds one consolidated results object per test combining
status + coverage + error message.

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
def analyze_session_coverage(session_id: str) -> dict:
    """
    Re-runs the test suite under coverage.py, targeting source.py, and
    builds a consolidated per-test object: test_id, status, coverage %,
    error message. Requires analyze_session_execution() to have already
    populated payload["test_execution"] for the status/error fields.
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
        }

    overall_line_coverage = overall.get("percent_covered")

    # Consolidate with test_execution results, if already run
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
        "consolidated_results": consolidated,
    }

    payload["coverage"] = result
    save_session(payload)
    return payload