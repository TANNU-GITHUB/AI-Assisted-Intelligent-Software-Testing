"""Walk a connected GitHub repo and run white-box + black-box testing on it."""

from __future__ import annotations

import json
from typing import Any, Callable

from agents.source_flatten import (
    combine_requirement_docs,
    fallback_requirements_from_functions,
    flatten_python_modules,
    is_python_source,
    is_requirement_doc,
    should_skip_path,
)
from auth.github_oauth import GitHubOAuthError, decode_github_file, github_request
from code_analysis.analyzer import analyze_session
from execution.analyzer import analyze_session_coverage, analyze_session_execution
from input_handler.handler import create_session, save_session, session_dir, session_with_files
from requirement_analysis.analyzer import analyze_session_requirements
from test_generation.black_box import analyze_session_black_box
from test_generation.gap_fill import analyze_session_gap_fill
from test_generation.other_tests import analyze_session_other_tests
from test_generation.white_box import analyze_session_white_box

MAX_PYTHON_FILES = 40
MAX_DOC_FILES = 12
MAX_BLOB_BYTES = 400_000


class GitHubProjectAgentError(RuntimeError):
    pass


def _repo_meta(token: str, owner: str, repo: str) -> dict[str, Any]:
    return github_request(token, f"/repos/{owner}/{repo}")


def _tree_blobs(token: str, owner: str, repo: str, branch: str) -> list[dict[str, Any]]:
    payload = github_request(token, f"/repos/{owner}/{repo}/git/trees/{branch}", {"recursive": "1"})
    if payload.get("truncated"):
        raise GitHubProjectAgentError(
            "Repository tree is too large to load in one request. Test a smaller repo or a subfolder."
        )
    blobs = []
    for item in payload.get("tree") or []:
        if not isinstance(item, dict) or item.get("type") != "blob":
            continue
        path = str(item.get("path") or "")
        if should_skip_path(path):
            continue
        size = int(item.get("size") or 0)
        blobs.append({"path": path, "size": size})
    return blobs


def _download(token: str, owner: str, repo: str, path: str) -> str:
    payload = github_request(token, f"/repos/{owner}/{repo}/contents/{path}")
    return decode_github_file(payload, max_bytes=MAX_BLOB_BYTES)


def collect_project_files(
    token: str,
    owner: str,
    repo: str,
    *,
    download: Callable[[str, str, str, str], str] | None = None,
) -> dict[str, Any]:
    fetch = download or _download
    try:
        meta = _repo_meta(token, owner, repo)
        branch = str(meta.get("default_branch") or "main")
        blobs = _tree_blobs(token, owner, repo, branch)
    except GitHubOAuthError as exc:
        raise GitHubProjectAgentError(str(exc)) from exc

    python_blobs = [item for item in blobs if is_python_source(item["path"])]
    doc_blobs = [item for item in blobs if is_requirement_doc(item["path"])]
    python_blobs.sort(key=lambda item: (item["size"], item["path"]))
    selected_py = python_blobs[:MAX_PYTHON_FILES]
    selected_docs = doc_blobs[:MAX_DOC_FILES]

    py_files: list[tuple[str, str]] = []
    doc_files: list[tuple[str, str]] = []
    errors: list[str] = []

    for item in selected_py:
        if item["size"] > MAX_BLOB_BYTES:
            errors.append(f"Skipped {item['path']} (larger than {MAX_BLOB_BYTES} bytes).")
            continue
        try:
            py_files.append((item["path"], fetch(token, owner, repo, item["path"])))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Could not read {item['path']}: {exc}")

    for item in selected_docs:
        if item["size"] > MAX_BLOB_BYTES:
            continue
        try:
            text = fetch(token, owner, repo, item["path"])
        except Exception:
            continue
        if is_requirement_doc(item["path"], text):
            doc_files.append((item["path"], text))

    flat = flatten_python_modules(py_files)
    requirements = combine_requirement_docs(doc_files)
    if not requirements.strip():
        requirements = fallback_requirements_from_functions(flat["included"])

    return {
        "owner": owner,
        "repo": repo,
        "full_name": f"{owner}/{repo}",
        "default_branch": branch,
        "tree_file_count": len(blobs),
        "python_file_count": len(python_blobs),
        "python_files_tested": [path for path, _text in py_files],
        "requirement_files": [path for path, _text in doc_files],
        "truncated_python": max(0, len(python_blobs) - len(selected_py)),
        "flatten": flat,
        "requirements_text": requirements,
        "download_errors": errors,
    }


def _run_stage(name: str, stages: list[dict[str, Any]], fn) -> None:
    try:
        fn()
        stages.append({"name": name, "status": "ok"})
    except Exception as exc:  # noqa: BLE001
        stages.append({"name": name, "status": "error", "detail": str(exc)})


def run_github_project_agent(
    *,
    token: str,
    owner: str,
    repo: str,
    owner_user_id: str,
) -> dict[str, Any]:
    collected = collect_project_files(token, owner, repo)
    flat = collected["flatten"]
    session = create_session(
        source_code=flat["source_code"],
        requirements_text=collected["requirements_text"],
        original_filename=f"{repo}_combined.py",
        owner_user_id=owner_user_id,
    )
    session_id = session["session_id"]
    folder = session_dir(session_id)
    project_dir = folder / "project"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "inventory.json").write_text(
        json.dumps(
            {
                "full_name": collected["full_name"],
                "python_files_tested": collected["python_files_tested"],
                "requirement_files": collected["requirement_files"],
                "included": flat["included"],
                "skipped": flat["skipped"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    stages: list[dict[str, Any]] = [{"name": "collect", "status": "ok"}]
    _run_stage("code_analysis", stages, lambda: analyze_session(session_id))
    _run_stage("requirement_analysis", stages, lambda: analyze_session_requirements(session_id))
    _run_stage("white_box", stages, lambda: analyze_session_white_box(session_id))
    _run_stage("black_box", stages, lambda: analyze_session_black_box(session_id))
    _run_stage("other_tests", stages, lambda: analyze_session_other_tests(session_id))
    _run_stage("execute", stages, lambda: analyze_session_execution(session_id))
    _run_stage("coverage", stages, lambda: analyze_session_coverage(session_id))
    missing = (session_with_files(session_id).get("coverage") or {}).get("missing_lines") or []
    untested = (session_with_files(session_id).get("requirement_coverage") or {}).get("untested_count") or 0
    if missing or untested:
        _run_stage("gap_fill", stages, lambda: analyze_session_gap_fill(session_id))
        _run_stage("execute_after_gap_fill", stages, lambda: analyze_session_execution(session_id))
        _run_stage("coverage_after_gap_fill", stages, lambda: analyze_session_coverage(session_id))

    payload = session_with_files(session_id)
    payload["github_agent"] = {
        "full_name": collected["full_name"],
        "default_branch": collected["default_branch"],
        "tree_file_count": collected["tree_file_count"],
        "python_file_count": collected["python_file_count"],
        "python_files_tested": collected["python_files_tested"],
        "requirement_files": collected["requirement_files"],
        "truncated_python": collected["truncated_python"],
        "included_modules": flat["included"],
        "skipped_modules": flat["skipped"],
        "download_errors": collected["download_errors"],
        "stages": stages,
        "function_count": flat["function_count"],
    }
    payload["status"] = "github_project_tested"
    save_session(payload)
    return session_with_files(session_id)
