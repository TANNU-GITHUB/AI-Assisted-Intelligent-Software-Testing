"""Turn pytest failures into short, actionable explanations."""

from __future__ import annotations

import re
from typing import Any


def parse_failure(longrepr: str | None) -> dict[str, str | None]:
    text = (longrepr or "").strip()
    if not text:
        return {
            "summary": "No error details were reported.",
            "expected": None,
            "actual": None,
            "exception_type": None,
            "hint": "Re-run analysis and inspect the generated pytest file for this case.",
        }

    compact = _compact(text)
    if "DID NOT RAISE" in text.upper():
        match = re.search(r"DID NOT RAISE\s+(\w+)", text, re.IGNORECASE)
        expected_exc = match.group(1) if match else "an error"
        return {
            "summary": f"The test expected {expected_exc}, but the code accepted the input.",
            "expected": expected_exc,
            "actual": "no exception",
            "exception_type": "Failed",
            "hint": (
                "The requirement says this input should be rejected. "
                "Add a guard in source.py that raises the expected error for this case."
            ),
        }

    assert_eq = re.search(
        r"AssertionError:\s*assert\s+(.*?)\s+==\s+(.*?)(?:\n|$)",
        text,
    )
    if assert_eq:
        actual = assert_eq.group(1).strip()
        expected = assert_eq.group(2).strip()
        return {
            "summary": f"Code returned {actual}, but the test expected {expected}.",
            "expected": expected,
            "actual": actual,
            "exception_type": "AssertionError",
            "hint": (
                "The generated test encodes the requirement or observed branch outcome. "
                "Change source.py so this input produces the expected result, then re-run."
            ),
        }

    assert_generic = re.search(r"AssertionError:\s*(.+)", text)
    if assert_generic:
        detail = assert_generic.group(1).strip()
        return {
            "summary": f"Assertion failed: {detail}",
            "expected": None,
            "actual": None,
            "exception_type": "AssertionError",
            "hint": "Update the function so it matches the requirement, then re-run analysis.",
        }

    exc = re.search(r"^E\s+(\w+(?:Error|Exception|Warning)):\s*(.+)$", text, re.MULTILINE)
    if not exc:
        exc = re.search(r"(\w+(?:Error|Exception)):\s*(.+)", text)
    if exc:
        exc_type, message = exc.group(1), exc.group(2).strip()
        return {
            "summary": f"{exc_type}: {message}",
            "expected": None,
            "actual": None,
            "exception_type": exc_type,
            "hint": (
                f"The function raised {exc_type}. If that is incorrect for this input, "
                "handle the case in source.py; if the spec requires the error, the test is right."
            ),
        }

    return {
        "summary": compact[:400],
        "expected": None,
        "actual": None,
        "exception_type": None,
        "hint": "Inspect the traceback, fix source.py to match the requirement, then re-run.",
    }


def _compact(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    interesting = [line.lstrip("E ").strip() for line in lines if line.startswith("E ") or "Error" in line]
    if interesting:
        return " | ".join(interesting[:4])
    return " ".join(lines[-8:])[:600]


def enrich_test_result(test: dict[str, Any], requirements: list[dict[str, Any]]) -> dict[str, Any]:
    req_by_id = {
        str(item.get("requirement_id")): item
        for item in requirements
        if isinstance(item, dict) and item.get("requirement_id")
    }
    req = req_by_id.get(str(test.get("requirement_id") or ""))
    failed = test.get("status") in {"failed", "error"}
    diagnosis = parse_failure(test.get("error_message") if failed else None)
    if req:
        test["requirement_condition"] = req.get("condition")
        test["requirement_expected"] = req.get("expected_result")
    if failed:
        test["why_failed"] = diagnosis["summary"]
        test["how_to_fix"] = diagnosis["hint"]
        test["expected_value"] = diagnosis["expected"]
        test["actual_value"] = diagnosis["actual"]
        if req:
            test["how_to_fix"] = (
                f"Requirement {req.get('requirement_id')} — {req.get('condition')}: "
                f"expected “{req.get('expected_result')}”. {diagnosis['hint']}"
            )
    else:
        test["why_failed"] = None
        test["how_to_fix"] = None
    return test


def build_requirement_coverage(
    requirements: list[dict[str, Any]],
    tests: list[dict[str, Any]],
    generated_ids: set[str] | None = None,
) -> dict[str, Any]:
    generated_ids = generated_ids or set()
    rows = []
    for item in requirements:
        if not isinstance(item, dict):
            continue
        req_id = str(item.get("requirement_id") or "").strip()
        if not req_id:
            continue
        linked = [t for t in tests if t.get("requirement_id") == req_id]
        failed = [t for t in linked if t.get("status") in {"failed", "error"}]
        if failed:
            status = "failed"
        elif linked:
            status = "passed"
        elif req_id in generated_ids:
            status = "generated_not_run"
        else:
            status = "untested"
        rows.append(
            {
                "requirement_id": req_id,
                "condition": item.get("condition"),
                "expected_result": item.get("expected_result"),
                "status": status,
                "test_count": len(linked),
                "failed_count": len(failed),
                "tests": [
                    {
                        "test_id": t.get("test_id"),
                        "status": t.get("status"),
                        "why_failed": t.get("why_failed"),
                    }
                    for t in linked
                ],
            }
        )
    tested = sum(1 for row in rows if row["status"] in {"passed", "failed"})
    return {
        "requirement_count": len(rows),
        "tested_count": tested,
        "passed_count": sum(1 for row in rows if row["status"] == "passed"),
        "failed_count": sum(1 for row in rows if row["status"] == "failed"),
        "untested_count": sum(1 for row in rows if row["status"] == "untested"),
        "coverage_percent": round(100.0 * tested / len(rows), 1) if rows else None,
        "requirements": rows,
    }


def collected_requirement_ids(payload: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for bucket in (
        (payload.get("white_box_tests") or {}).get("test_cases") or [],
        (payload.get("black_box_tests") or {}).get("test_cases") or [],
        (payload.get("other_tests") or {}).get("integration_tests") or [],
        (payload.get("other_tests") or {}).get("negative_tests") or [],
    ):
        for case in bucket:
            if isinstance(case, dict) and case.get("requirement_id"):
                ids.add(str(case["requirement_id"]))
    return ids
