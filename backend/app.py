"""FastAPI entry point for Tasks 1–4 — used by the Next.js frontend."""

from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from code_analysis.analyzer import CodeAnalysisError, analyze_session
from config import ROOT_DIR
from input_handler.handler import (
    InputValidationError,
    create_session,
    list_sessions,
    session_with_files,
)
from pipeline import run_phase1
from requirement_analysis.analyzer import RequirementAnalysisError, analyze_session_requirements

app = FastAPI(
    title="AI-Assisted Intelligent Software Testing",
    description="Phase 1 API: input handling, source-code analysis, requirement analysis.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _as_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@app.get("/health")
@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/examples")
def get_examples() -> dict[str, str]:
    return {
        "filename": "sample_source.py",
        "source_code": (ROOT_DIR / "examples" / "sample_source.py").read_text(encoding="utf-8"),
        "requirements_text": (ROOT_DIR / "examples" / "sample_requirements.txt").read_text(
            encoding="utf-8"
        ),
    }


@app.get("/api/sessions")
def get_sessions() -> dict:
    return {"sessions": list_sessions()}


@app.post("/api/sessions")
async def create_analysis_session(
    source_file: UploadFile = File(...),
    requirements_text: str = Form(...),
    run_analysis: str = Form("false"),
):
    filename = source_file.filename or "source.py"
    raw = await source_file.read()
    try:
        source_code = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Source file must be UTF-8 text.") from exc

    try:
        if _as_bool(run_analysis):
            payload = run_phase1(
                source_code=source_code,
                requirements_text=requirements_text,
                original_filename=filename,
            )
        else:
            payload = create_session(
                source_code=source_code,
                requirements_text=requirements_text,
                original_filename=filename,
            )
        return session_with_files(payload["session_id"])
    except (InputValidationError, CodeAnalysisError, RequirementAnalysisError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    try:
        return session_with_files(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/sessions/{session_id}/code-analysis")
def run_code_analysis(session_id: str):
    try:
        analyze_session(session_id)
        return session_with_files(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CodeAnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/sessions/{session_id}/requirement-analysis")
def run_requirement_analysis(session_id: str):
    try:
        analyze_session_requirements(session_id)
        return session_with_files(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RequirementAnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
