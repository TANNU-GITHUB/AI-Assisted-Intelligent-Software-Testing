"""Orchestrator for Tasks 1–4: input → code analysis → requirement analysis."""

from __future__ import annotations

from typing import Any

from code_analysis.analyzer import analyze_session
from input_handler.handler import create_session, load_session
from requirement_analysis.analyzer import analyze_session_requirements


def run_phase1(
    *,
    source_code: str,
    requirements_text: str,
    original_filename: str = "source.py",
) -> dict[str, Any]:
    session = create_session(
        source_code=source_code,
        requirements_text=requirements_text,
        original_filename=original_filename,
    )
    session_id = session["session_id"]
    analyze_session(session_id)
    analyze_session_requirements(session_id)
    return load_session(session_id)
