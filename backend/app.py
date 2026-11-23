"""FastAPI entry point for Tasks 1–4 — used by the Next.js frontend."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from llm_client import LLMError


from auth.github_routes import router as github_router
from auth.routes import get_current_user, router as auth_router
from auth.session_access import assert_session_owner
from auth.store import UserRecord, init_db
from code_analysis.analyzer import CodeAnalysisError, analyze_session
from config import ROOT_DIR
from input_handler.documents import (
    DocumentExtractError,
    DocumentVisionError,
    extract_requirements_text,
)
from requirement_analysis.diagram_extractor import (
    DiagramExtractionError,
    extract_requirements_from_diagram,
    requirements_to_text,
)
from input_handler.handler import (
    InputValidationError,
    create_session,
    list_sessions,
    session_with_files,
    update_session_source,
)
from pipeline import run_phase1


logger = logging.getLogger(__name__)
from requirement_analysis.analyzer import RequirementAnalysisError, analyze_session_requirements
from test_generation.black_box import BlackBoxError, analyze_session_black_box
from test_generation.gap_fill import GapFillError, analyze_session_gap_fill
from test_generation.other_tests import OtherTestsError, analyze_session_other_tests
from test_generation.white_box import WhiteBoxError, analyze_session_white_box
from execution.analyzer import CoverageError, ExecutionError, analyze_session_coverage, analyze_session_execution
from reporting.analyzer import render_session_report


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI-Assisted Intelligent Software Testing",
    description="Phase 1 API: input handling, source-code analysis, requirement analysis.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(github_router)

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


@app.get("/api/status/llm")
def llm_status() -> dict:
    """Return whether each LLM provider is reachable. Used by the frontend to show helpful errors."""
    from llm_client import (
        NVIDIA_API_KEY as _nv_key,
        OLLAMA_BASE_URL as _ollama_url,
        OLLAMA_MODEL as _ollama_model,
        PLACEHOLDER_KEYS,
        _is_ollama_online,
        _resolve_available_ollama_model,
        is_nvidia_exhausted,
    )
    nvidia_configured = bool(_nv_key and _nv_key not in PLACEHOLDER_KEYS)
    nvidia_available = nvidia_configured and not is_nvidia_exhausted()
    ollama_online = _is_ollama_online()
    ollama_model = _resolve_available_ollama_model(_ollama_model) if ollama_online else _ollama_model
    return {
        "nvidia": {
            "configured": nvidia_configured,
            "available": nvidia_available,
            "exhausted": nvidia_configured and is_nvidia_exhausted(),
        },
        "ollama": {
            "url": _ollama_url,
            "online": ollama_online,
            "model": ollama_model,
        },
        "any_llm_available": nvidia_available or ollama_online,
        "hint": (
            None if (nvidia_available or ollama_online)
            else (
                "No LLM is reachable. "
                "Either set NVIDIA_API_KEY in backend/.env, or install Ollama from "
                "https://ollama.com and run: ollama pull llama3.2"
            )
        ),
    }


@app.post("/api/requirements/extract")
async def extract_requirements_document(
    requirements_file: UploadFile = File(...),
    user: UserRecord = Depends(get_current_user),
) -> dict[str, str]:
    _ = user
    filename = requirements_file.filename or "requirements.bin"
    raw = await requirements_file.read()
    try:
        text = extract_requirements_text(filename, raw)
    except DocumentVisionError:
        # Vision enhancement failed — the PDF text was still extracted.
        # Re-run without vision by calling the PDF text path only.
        try:
            from input_handler.documents import _from_plain, _from_pdf, _from_docx, _from_doc, _normalize
            suffix = ("." + filename.rsplit(".", 1)[-1]).lower() if "." in filename else ""
            if suffix == ".pdf":
                text = _normalize(_from_pdf(raw))
            elif suffix == ".docx":
                text = _normalize(_from_docx(raw))
            elif suffix == ".doc":
                text = _normalize(_from_doc(raw))
            else:
                text = _normalize(_from_plain(raw))
            if not text:
                raise DocumentExtractError("No readable text was found in that file.")
        except DocumentExtractError as exc2:
            raise HTTPException(status_code=400, detail=str(exc2)) from exc2
    except DocumentExtractError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"filename": filename, "requirements_text": text}


_ALLOWED_IMAGE_TYPES: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
_IMAGE_EXT_MAP: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


@app.post("/api/requirements/extract-diagram")
async def extract_diagram_requirements(
    diagram_file: UploadFile = File(...),
) -> dict:
    """Extract testable requirements from an uploaded diagram or flowchart image."""
    content_type = (diagram_file.content_type or "").lower().split(";")[0].strip()
    fname = (diagram_file.filename or "").lower()

    # Infer MIME from extension when browser sends a generic type
    if content_type not in _ALLOWED_IMAGE_TYPES:
        for ext, ct in _IMAGE_EXT_MAP.items():
            if fname.endswith(ext):
                content_type = ct
                break
        else:
            raise HTTPException(
                status_code=400,
                detail="Please upload a PNG, JPEG, GIF, or WEBP image.",
            )

    raw = await diagram_file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 10 MB.")

    try:
        result = extract_requirements_from_diagram(raw, content_type)
    except DiagramExtractionError as exc:
        logger.warning("Diagram requirements extraction failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    req_text = (result.get("plain_text") or "").strip() or requirements_to_text(
        result.get("requirements", [])
    )
    return {
        "filename": diagram_file.filename or "diagram",
        "requirements_text": req_text,
        "structured": result,
        "model": result.get("model"),
    }


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
def get_sessions(user: UserRecord = Depends(get_current_user)) -> dict:
    return {"sessions": list_sessions(owner_user_id=user.id)}


@app.post("/api/sessions")
async def create_analysis_session(
    source_file: UploadFile = File(...),
    requirements_text: str = Form(...),
    run_analysis: str = Form("false"),
    user: UserRecord = Depends(get_current_user),
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
                owner_user_id=user.id,
            )
        else:
            payload = create_session(
                source_code=source_code,
                requirements_text=requirements_text,
                original_filename=filename,
                owner_user_id=user.id,
            )
        return session_with_files(payload["session_id"])
    except (InputValidationError, CodeAnalysisError, RequirementAnalysisError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise _session_step_error(exc) from exc


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str, user: UserRecord = Depends(get_current_user)):
    try:
        assert_session_owner(session_id, user)
        return session_with_files(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/api/sessions/{session_id}/source")
def update_source(
    session_id: str,
    body: dict,
    user: UserRecord = Depends(get_current_user),
):
    source_code = body.get("source_code")
    if not isinstance(source_code, str):
        raise HTTPException(status_code=400, detail="source_code must be a string.")
    try:
        assert_session_owner(session_id, user)
        update_session_source(session_id, source_code)
        return session_with_files(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InputValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/sessions/{session_id}/report", response_class=HTMLResponse)
def get_session_report(session_id: str, user: UserRecord = Depends(get_current_user)):
    try:
        assert_session_owner(session_id, user)
        html = render_session_report(session_id)
        return HTMLResponse(content=html, headers={"Content-Disposition": "attachment; filename=test-report.html"})
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)[:500]) from exc


def _protected_session(session_id: str, user: UserRecord) -> None:
    assert_session_owner(session_id, user)


def _session_step_error(exc: Exception) -> HTTPException:
    logger.exception("Session step failed: %s", exc)
    if isinstance(exc, LLMError):
        return HTTPException(
            status_code=503,
            detail=str(exc),
        )
    return HTTPException(
        status_code=400,
        detail=f"{type(exc).__name__}: {str(exc)[:500]}",
    )


@app.post("/api/sessions/{session_id}/code-analysis")
def run_code_analysis(session_id: str, user: UserRecord = Depends(get_current_user)):
    try:
        _protected_session(session_id, user)
        analyze_session(session_id)
        return session_with_files(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CodeAnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise _session_step_error(exc) from exc


@app.post("/api/sessions/{session_id}/requirement-analysis")
def run_requirement_analysis(session_id: str, user: UserRecord = Depends(get_current_user)):
    try:
        _protected_session(session_id, user)
        analyze_session_requirements(session_id)
        return session_with_files(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/api/sessions/{session_id}/white-box-tests")
def run_white_box_tests(session_id: str, user: UserRecord = Depends(get_current_user)):
    try:
        _protected_session(session_id, user)
        analyze_session_white_box(session_id)
        return session_with_files(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WhiteBoxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise _session_step_error(exc) from exc


@app.post("/api/sessions/{session_id}/black-box-tests")
def run_black_box_tests(session_id: str, user: UserRecord = Depends(get_current_user)):
    try:
        _protected_session(session_id, user)
        analyze_session_black_box(session_id)
        return session_with_files(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BlackBoxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise _session_step_error(exc) from exc


@app.post("/api/sessions/{session_id}/other-tests")
def run_other_tests(session_id: str, user: UserRecord = Depends(get_current_user)):
    try:
        _protected_session(session_id, user)
        analyze_session_other_tests(session_id)
        return session_with_files(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OtherTestsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise _session_step_error(exc) from exc

@app.post("/api/sessions/{session_id}/execute-tests")
def run_execute_tests(session_id: str, user: UserRecord = Depends(get_current_user)):
    try:
        _protected_session(session_id, user)
        analyze_session_execution(session_id)
        return session_with_files(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ExecutionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise _session_step_error(exc) from exc
    
@app.post("/api/sessions/{session_id}/gap-fill-tests")
def run_gap_fill_tests(session_id: str, user: UserRecord = Depends(get_current_user)):
    try:
        _protected_session(session_id, user)
        analyze_session_gap_fill(session_id)
        return session_with_files(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GapFillError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise _session_step_error(exc) from exc


@app.post("/api/sessions/{session_id}/coverage")
def run_coverage(session_id: str, user: UserRecord = Depends(get_current_user)):
    try:
        _protected_session(session_id, user)
        analyze_session_coverage(session_id)
        return session_with_files(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CoverageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise _session_step_error(exc) from exc


def _register_llm_exception_handlers(application: FastAPI) -> None:
    import traceback

    @application.exception_handler(LLMError)
    async def _llm_error(_request, exc: LLMError):
        return JSONResponse(
            status_code=503,
            content={"detail": (
                f"{exc} "
                "— Install Ollama from https://ollama.com and run: "
                "ollama pull llama3.2  (then restart the backend)"
            )},
        )

    @application.exception_handler(Exception)
    async def _global_error_handler(_request, exc: Exception):
        if isinstance(exc, HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=getattr(exc, "headers", None),
            )
        if isinstance(exc, LLMError):
            return JSONResponse(
                status_code=503,
                content={"detail": str(exc)},
            )
        logger.error("Unhandled server exception: %s\n%s", exc, traceback.format_exc())
        return JSONResponse(
            status_code=400,
            content={"detail": f"{type(exc).__name__}: {str(exc)[:500]}"},
        )


_register_llm_exception_handlers(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_excludes=["sessions", "data", "sessions/*", "*.json"],
    )
