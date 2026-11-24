"""Task 2 — Input handling: validate uploads, persist a session folder, return session_id."""

from __future__ import annotations

import json
import os
import uuid
import difflib
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Callable, Concatenate, ParamSpec, TypeVar

from filelock import FileLock

from agents.source_flatten import fit_python_source
from config import SCHEMA_VERSION, SESSIONS_DIR


class InputValidationError(ValueError):
    """Raised when uploaded source code or requirements fail validation."""


P = ParamSpec("P")
R = TypeVar("R")
_ACTIVE_SESSION_LOCKS: ContextVar[dict[str, FileLock]] = ContextVar(
    "active_session_locks", default={}
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_session_id() -> str:
    return uuid.uuid4().hex[:12]


def session_dir(session_id: str) -> Path:
    return SESSIONS_DIR / session_id


def session_manifest_path(session_id: str) -> Path:
    return session_dir(session_id) / "session.json"


def _session_lock(session_id: str) -> FileLock:
    active_locks = _ACTIVE_SESSION_LOCKS.get()
    return active_locks.get(session_id) or FileLock(
        str(session_manifest_path(session_id)) + ".lock"
    )


def session_locked(
    function: Callable[Concatenate[str, P], R],
) -> Callable[Concatenate[str, P], R]:
    @wraps(function)
    def wrapper(session_id: str, *args: P.args, **kwargs: P.kwargs) -> R:
        active_locks = _ACTIVE_SESSION_LOCKS.get()
        if session_id in active_locks:
            return function(session_id, *args, **kwargs)

        lock = _session_lock(session_id)
        with lock:
            token = _ACTIVE_SESSION_LOCKS.set({**active_locks, session_id: lock})
            try:
                return function(session_id, *args, **kwargs)
            finally:
                _ACTIVE_SESSION_LOCKS.reset(token)

    return wrapper


def load_session(session_id: str) -> dict:
    path = session_manifest_path(session_id)
    if not path.is_file():
        raise FileNotFoundError(f"Unknown session_id: {session_id}")
    with _session_lock(session_id):
        return json.loads(path.read_text(encoding="utf-8"))


def session_with_files(session_id: str) -> dict:
    payload = load_session(session_id)
    folder = session_dir(session_id)
    payload["source_code"] = (folder / "source.py").read_text(encoding="utf-8")
    payload["requirements_text"] = (folder / "requirements.txt").read_text(encoding="utf-8")
    return payload


def list_sessions(owner_user_id: str | None = None) -> list[dict]:
    if not SESSIONS_DIR.exists():
        return []
    items: list[dict] = []
    for folder in SESSIONS_DIR.iterdir():
        if not folder.is_dir():
            continue
        manifest = folder / "session.json"
        if not manifest.is_file():
            continue
        with _session_lock(folder.name):
            data = json.loads(manifest.read_text(encoding="utf-8"))
        if owner_user_id and data.get("owner_user_id") != owner_user_id:
            continue
        items.append(
            {
                "session_id": data.get("session_id", folder.name),
                "status": data.get("status"),
                "created_at": data.get("created_at"),
                "original_filename": (data.get("inputs") or {}).get("original_filename"),
                "function_count": (data.get("code_analysis") or {}).get("function_count"),
                "requirement_count": (data.get("requirement_analysis") or {}).get(
                    "requirement_count"
                ),
            }
        )
    items.sort(key=lambda row: row.get("created_at") or "", reverse=True)
    return items


def save_session(payload: dict) -> dict:
    session_id = payload["session_id"]
    payload["updated_at"] = _utc_now()
    folder = session_dir(session_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = session_manifest_path(session_id)
    data = json.dumps(payload, indent=2, ensure_ascii=False)
    with _session_lock(session_id):
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(data, encoding="utf-8")
        os.replace(temp_path, path)
    return payload


def _validate_source(filename: str, source_code: str) -> None:
    if not filename or not filename.lower().endswith(".py"):
        raise InputValidationError("Only Python source files (.py) are accepted.")
    if not source_code or not source_code.strip():
        raise InputValidationError("The uploaded source file is empty.")


def _validate_requirements(requirements_text: str) -> None:
    if not requirements_text or not requirements_text.strip():
        raise InputValidationError("Requirements text cannot be empty.")


MAX_SOURCE_CHARS = 350_000
MAX_REQUIREMENTS_CHARS = 50_000


def create_session(
    *,
    source_code: str,
    requirements_text: str,
    original_filename: str = "source.py",
    owner_user_id: str | None = None,
) -> dict:
    """Validate inputs, write session files, and return the shared JSON payload."""
    if len(source_code) > MAX_SOURCE_CHARS:
        source_code = fit_python_source(source_code, MAX_SOURCE_CHARS)
    if len(requirements_text) > MAX_REQUIREMENTS_CHARS:
        requirements_text = (
            requirements_text[:MAX_REQUIREMENTS_CHARS]
            + "\n# ... (requirements truncated at 50,000 characters) ...\n"
        )
    _validate_source(original_filename, source_code)
    _validate_requirements(requirements_text)

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    session_id = _new_session_id()
    folder = session_dir(session_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "logs").mkdir(exist_ok=True)
    regression_dir = folder / "regression"
    regression_dir.mkdir(exist_ok=True)
    (folder / "tests" / "white_box").mkdir(parents=True, exist_ok=True)
    (folder / "tests" / "black_box").mkdir(parents=True, exist_ok=True)
    (folder / "tests" / "gray_box").mkdir(parents=True, exist_ok=True)

    source_path = folder / "source.py"
    requirements_path = folder / "requirements.txt"
    source_path.write_text(source_code, encoding="utf-8")
    (regression_dir / "source_snapshot.py").write_text(source_code, encoding="utf-8")
    requirements_path.write_text(requirements_text.strip() + "\n", encoding="utf-8")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "session_id": session_id,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "status": "created",
        "inputs": {
            "source_filename": "source.py",
            "source_path": str(source_path),
            "requirements_path": str(requirements_path),
            "original_filename": Path(original_filename).name,
        },
        "code_analysis": None,
        "requirement_analysis": None,
        "errors": [],
        "owner_user_id": owner_user_id,
    }
    return save_session(payload)


@session_locked
def update_session_source(session_id: str, source_code: str) -> dict:
    if len(source_code) > MAX_SOURCE_CHARS:
        source_code = fit_python_source(source_code, MAX_SOURCE_CHARS)
    payload = load_session(session_id)
    original_filename = (payload.get("inputs") or {}).get("original_filename", "source.py")
    _validate_source(original_filename, source_code)

    from code_analysis.analyzer import CodeAnalysisError, analyze_source

    try:
        analysis = analyze_source(source_code)
    except CodeAnalysisError as exc:
        raise InputValidationError(str(exc)) from exc

    folder = session_dir(session_id)
    snapshot_path = folder / "regression" / "source_snapshot.py"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    previous_source = (
        snapshot_path.read_text(encoding="utf-8") if snapshot_path.is_file() else ""
    )
    source_changed = previous_source != source_code
    source_diff = ""
    if source_changed:
        source_diff = "".join(
            difflib.unified_diff(
                previous_source.splitlines(keepends=True),
                source_code.splitlines(keepends=True),
                fromfile="stored/source.py",
                tofile="updated/source.py",
            )
        )

    (folder / "source.py").write_text(source_code, encoding="utf-8")
    payload["code_analysis"] = analysis
    payload["status"] = (
        "ready_for_test_generation"
        if payload.get("requirement_analysis")
        else "code_analyzed"
    )
    save_session(payload)

    if source_changed:
        from datetime import datetime, timezone

        from input_handler.session_logging import log_session_error

        tests_dir = folder / "tests"
        existing_tests = list(tests_dir.rglob("test_*.py")) if tests_dir.is_dir() else []
        regression_result = {"status": "no_existing_tests", "total": 0, "tests": []}
        execution_completed = not existing_tests
        if existing_tests:
            try:
                from execution.analyzer import analyze_session_execution

                payload = analyze_session_execution(session_id)
                regression_result = payload.get("test_execution", {})
                execution_completed = True
            except Exception as exc:
                log_session_error(session_id, "source_update.regression", exc)
                regression_result = {"status": "error", "error": str(exc), "tests": []}

        payload["regression_awareness"] = {
            "source_changed": True,
            "source_diff": source_diff,
            "execution": regression_result,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        if execution_completed:
            snapshot_path.write_text(source_code, encoding="utf-8")
        save_session(payload)

    return payload
