"""Extra tests for uncovered source lines and untested requirements."""

from __future__ import annotations

import ast
import re
from typing import Any

from input_handler.handler import load_session, save_session, session_dir
from test_generation.black_box import _fallback_cases as _black_box_fallback
from test_generation.white_box import _fallback_cases as _white_box_fallback


class GapFillError(Exception):
    pass


def _write_gap_pytest(session_id: str, cases: list[dict[str, Any]]) -> str:
    out_dir = session_dir(session_id) / "tests" / "gap_fill"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "test_gap_fill.py"
    lines = [
        "import sys",
        "from pathlib import Path",
        "import pytest",
        "",
        "sys.path.insert(0, str(Path(__file__).resolve().parents[2]))",
        "from source import *",
        "",
    ]
    for index, case in enumerate(cases, start=1):
        function_name = case.get("function_name") or "target"
        req_id = case.get("requirement_id") or "REQ-01"
        safe = re.sub(r"[^a-zA-Z0-9_]+", "_", f"{function_name}_{req_id}_{index}")
        inputs = case.get("input") or {}
        lines.append(
            f"@pytest.mark.parametrize('_requirement_id', [{req_id!r}], ids=[{req_id!r}])"
        )
        lines.append(f"def test_gap_{safe}(_requirement_id):")
        if case.get("expected_exception"):
            lines.append(f"    with pytest.raises({case['expected_exception']}):")
            lines.append(f"        {function_name}(**{inputs!r})")
        elif "expected_output" in case and case.get("expected_output") is not None:
            lines.append(f"    assert {function_name}(**{inputs!r}) == {case['expected_output']!r}")
        else:
            lines.append(f"    {function_name}(**{inputs!r})")
        lines.append("")
    tmp = out_file.with_suffix(out_file.suffix + ".tmp")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    tmp.replace(out_file)
    return str(out_file)


def analyze_session_gap_fill(session_id: str) -> dict:
    payload = load_session(session_id)
    folder = session_dir(session_id)
    source_path = folder / "source.py"
    if not source_path.is_file():
        raise FileNotFoundError(f"source.py not found for session '{session_id}'.")
    source_code = source_path.read_text(encoding="utf-8")

    coverage = payload.get("coverage") or {}
    missing_lines = set(coverage.get("missing_lines") or [])
    functions = (payload.get("code_analysis") or {}).get("functions") or []
    requirements = (payload.get("requirement_analysis") or {}).get("requirements") or []
    req_ids = [str(r.get("requirement_id")) for r in requirements if r.get("requirement_id")]
    req_cov_rows = (payload.get("requirement_coverage") or {}).get("requirements") or []
    untested = [
        row
        for row in req_cov_rows
        if row.get("status") in {"untested", "generated_not_run"}
    ]
    if not untested:
        tested_ids = {
            t.get("requirement_id")
            for t in (payload.get("test_execution") or {}).get("tests") or []
            if t.get("requirement_id")
        }
        untested = [
            req
            for req in requirements
            if isinstance(req, dict) and req.get("requirement_id") not in tested_ids
        ]

    extra_cases: list[dict[str, Any]] = []
    for fn in functions:
        if fn.get("is_async") or "." in (fn.get("qualified_name") or ""):
            continue
        start, end = fn.get("lineno", 0), fn.get("end_lineno", 0)
        if missing_lines and not any(start <= line <= end for line in missing_lines):
            continue
        try:
            cases = _white_box_fallback(fn, source_code)
        except Exception:
            continue
        for index, case in enumerate(cases):
            case["requirement_id"] = req_ids[index % len(req_ids)] if req_ids else "REQ-01"
        extra_cases.extend(cases)

    if untested:
        catalog = [
            {
                "name": fn["name"],
                "params": fn.get("params") or [],
                "return_type": fn.get("return_type"),
            }
            for fn in functions
            if not fn.get("is_async") and "." not in (fn.get("qualified_name") or fn["name"])
        ]
        if not catalog:
            tree = ast.parse(source_code)
            catalog = [
                {
                    "name": node.name,
                    "params": [{"name": arg.arg} for arg in node.args.args],
                    "return_type": None,
                }
                for node in tree.body
                if isinstance(node, ast.FunctionDef)
            ]
        structured = [
            {
                "requirement_id": str(item.get("requirement_id")),
                "condition": str(item.get("condition") or ""),
                "expected_result": str(item.get("expected_result") or ""),
            }
            for item in untested
            if item.get("requirement_id")
        ]
        try:
            extra_cases.extend(_black_box_fallback(structured, catalog, source_code))
        except Exception:
            pass

    files_written: list[str] = []
    if extra_cases:
        files_written.append(_write_gap_pytest(session_id, extra_cases))

    payload["gap_fill"] = {
        "extra_cases": len(extra_cases),
        "files_written": files_written,
        "missing_lines_targeted": sorted(missing_lines),
        "untested_requirements": [item.get("requirement_id") for item in untested],
    }
    payload["status"] = "gap_fill_generated"
    save_session(payload)
    return payload
