import pytest

import execution.analyzer as execution_analyzer
from input_handler.handler import create_session
from reporting.analyzer import build_report_data, render_session_report
from test_generation.other_tests import (
    OtherTestsError,
    _validate_test_cases,
    _write_pytest_file,
)


def test_report_data_links_tests_and_marks_flaky_cases():
    payload = {
        "session_id": "test123",
        "requirement_analysis": {
            "requirements": [
                {
                    "requirement_id": "REQ-01",
                    "condition": "input is accepted",
                    "expected_result": "returns true",
                }
            ]
        },
        "test_execution": {
            "total": 2,
            "passed": 1,
            "failed": 0,
            "errors": 0,
            "flaky": 1,
            "tests": [
                {
                    "test_id": "tests/test_example.py::test_valid[REQ-01]",
                    "requirement_id": "REQ-01",
                    "status": "passed",
                    "flaky": True,
                    "error_message": None,
                },
                {
                    "test_id": "tests/test_other.py::test_ok",
                    "status": "passed",
                    "flaky": False,
                },
            ],
        },
        "coverage": {
            "overall_line_coverage_percent": 80.0,
            "function_coverage": [
                {
                    "function": "validate",
                    "line_coverage_percent": 80.0,
                    "branch_count": 1,
                    "branches": [
                        {
                            "lineno": 4,
                            "condition": "value is not None",
                            "fully_covered": False,
                        }
                    ],
                }
            ],
        },
    }

    report = build_report_data(payload)

    assert report["traceability"][0]["tests"][0]["requirement_id"] == "REQ-01"
    assert report["traceability"][0]["flaky"] is True
    assert report["defects"] == []
    assert "Zero-coverage branch" in report["coverage_warnings"][0]


def test_report_endpoint_renders_saved_session(tmp_path, monkeypatch):
    from input_handler.handler import create_session, save_session

    monkeypatch.setattr("input_handler.handler.SESSIONS_DIR", tmp_path)
    payload = create_session(
        source_code="def add(a, b):\n    return a + b\n",
        requirements_text="Adding returns the sum.",
    )
    payload["requirement_analysis"] = {
        "requirements": [
            {
                "requirement_id": "REQ-01",
                "condition": "two numbers are added",
                "expected_result": "their sum is returned",
            }
        ]
    }
    payload["test_execution"] = {
        "total": 1,
        "passed": 1,
        "failed": 0,
        "errors": 0,
        "tests": [
            {
                "test_id": "test_add[REQ-01]",
                "requirement_id": "REQ-01",
                "status": "passed",
            }
        ],
    }
    save_session(payload)

    html = render_session_report(payload["session_id"])
    assert "Software Test Report" in html
    assert "REQ-01" in html
    assert "test_add[REQ-01]" in html


def test_test_generation_rejects_missing_or_unknown_requirement_id():
    with pytest.raises(OtherTestsError, match="missing requirement_id"):
        _validate_test_cases([{}], {"REQ-01"}, "integration")
    with pytest.raises(OtherTestsError, match="unknown requirement_id"):
        _validate_test_cases([{"requirement_id": "REQ-02"}], {"REQ-01"}, "negative")


def test_generated_pytest_file_includes_requirement_id(tmp_path, monkeypatch):
    monkeypatch.setattr("input_handler.handler.SESSIONS_DIR", tmp_path)
    path = _write_pytest_file(
        "session1",
        "integration",
        [
            {
                "caller": "combined",
                "input": {"value": 1},
                "expected_output": 1,
                "requirement_id": "REQ-01",
            }
        ],
    )
    from pathlib import Path

    generated = Path(path).read_text(encoding="utf-8")
    assert "ids=['REQ-01']" in generated
    assert "def test_integration_combined_case1(_requirement_id):" in generated


def test_execution_retries_only_failed_tests_and_marks_flaky(tmp_path, monkeypatch):
    monkeypatch.setattr("input_handler.handler.SESSIONS_DIR", tmp_path)
    payload = create_session(
        source_code="def value():\n    return 1\n",
        requirements_text="value returns one.",
    )
    tests_dir = tmp_path / payload["session_id"] / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "test_value.py").write_text("def test_value(): pass\n", encoding="utf-8")
    reports = iter(
        [
            {
                "summary": {"total": 2, "passed": 1, "failed": 1, "error": 0},
                "tests": [
                    {"nodeid": "test_value.py::test_ok", "outcome": "passed"},
                    {
                        "nodeid": "test_value.py::test_flaky[REQ-01]",
                        "outcome": "failed",
                        "call": {"longrepr": "first failure", "duration": 0.1},
                    },
                ],
            },
            {
                "tests": [
                    {
                        "nodeid": "test_value.py::test_flaky[REQ-01]",
                        "outcome": "passed",
                        "call": {"duration": 0.2},
                    }
                ]
            },
        ]
    )
    targets_seen = []

    def fake_run(folder, targets, report_path):
        targets_seen.append(targets)
        report_path.write_text("{}", encoding="utf-8")
        return next(reports)

    monkeypatch.setattr(execution_analyzer, "_run_pytest", fake_run)
    result = execution_analyzer.analyze_session_execution(payload["session_id"])

    tests = result["test_execution"]["tests"]
    flaky = next(test for test in tests if "test_flaky" in test["test_id"])
    assert len(targets_seen) == 2
    assert targets_seen[1] == ["test_value.py::test_flaky[REQ-01]"]
    assert flaky["requirement_id"] == "REQ-01"
    assert flaky["status"] == "passed"
    assert flaky["flaky"] is True
    assert result["test_execution"]["flaky"] == 1
    log_text = (tmp_path / payload["session_id"] / "logs" / "run.log").read_text(
        encoding="utf-8"
    )
    assert "test_value.py::test_flaky[REQ-01]" in log_text
    assert "first failure" in log_text


def test_source_update_runs_existing_regression_tests(tmp_path, monkeypatch):
    import execution.analyzer
    from input_handler.handler import update_session_source

    monkeypatch.setattr("input_handler.handler.SESSIONS_DIR", tmp_path)
    payload = create_session(
        source_code="def value():\n    return 1\n",
        requirements_text="value returns one.",
    )
    session_folder = tmp_path / payload["session_id"]
    tests_dir = session_folder / "tests"
    (tests_dir / "test_value.py").write_text("def test_value(): pass\n", encoding="utf-8")
    calls = []

    def fake_execution(session_id):
        calls.append(session_id)
        return {**payload, "test_execution": {"total": 1, "passed": 1, "tests": []}}

    monkeypatch.setattr(execution.analyzer, "analyze_session_execution", fake_execution)
    updated = update_session_source(
        payload["session_id"], "def value():\n    return 2\n"
    )

    assert calls == [payload["session_id"]]
    assert updated["regression_awareness"]["execution"]["passed"] == 1
    assert "+    return 2" in updated["regression_awareness"]["source_diff"]
    assert (session_folder / "regression" / "source_snapshot.py").read_text(
        encoding="utf-8"
    ).endswith("return 2\n")