from execution.diagnostics import build_requirement_coverage, parse_failure


def test_parse_assertion_explains_expected_vs_actual():
    raw = "E       AssertionError: assert 90.0 == 80.0\n"
    result = parse_failure(raw)
    assert "90.0" in result["summary"]
    assert result["expected"] == "80.0"
    assert result["actual"] == "90.0"
    assert "source.py" in (result["hint"] or "")


def test_parse_did_not_raise():
    result = parse_failure("Failed: DID NOT RAISE ValueError")
    assert "ValueError" in result["summary"]
    assert "reject" in (result["hint"] or "").lower()


def test_requirement_coverage_marks_untested_and_failed():
    requirements = [
        {"requirement_id": "REQ-01", "condition": "members get discount"},
        {"requirement_id": "REQ-02", "condition": "reject negatives"},
        {"requirement_id": "REQ-03", "condition": "empty cart is zero"},
    ]
    tests = [
        {"test_id": "t1", "requirement_id": "REQ-01", "status": "passed"},
        {
            "test_id": "t2",
            "requirement_id": "REQ-02",
            "status": "failed",
            "why_failed": "expected error",
        },
    ]
    coverage = build_requirement_coverage(requirements, tests, {"REQ-01", "REQ-02"})
    by_id = {row["requirement_id"]: row for row in coverage["requirements"]}
    assert by_id["REQ-01"]["status"] == "passed"
    assert by_id["REQ-02"]["status"] == "failed"
    assert by_id["REQ-03"]["status"] == "untested"
    assert coverage["untested_count"] == 1
