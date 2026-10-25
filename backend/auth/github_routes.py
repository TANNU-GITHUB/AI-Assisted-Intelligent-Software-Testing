"""GitHub connect + repository browsing for Live Lab imports."""

from __future__ import annotations

import base64
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.github_oauth import (
    GitHubOAuthError,
    consume_github_state,
    create_github_auth_url,
    exchange_code_for_github,
    github_request,
)
from auth.routes import get_current_user
from auth.store import (
    UserRecord,
    delete_github_connection,
    get_github_connection,
    get_github_public,
    upsert_github_connection,
)
from auth.token_crypto import decrypt_secret, encrypt_secret

router = APIRouter(prefix="/api/github", tags=["github"])

_REPO_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
_MAX_FILE_BYTES = 400_000
_SOURCE_SUFFIXES = {".py"}
_REQ_NAMES = {"requirements.txt", "requirement.txt", "spec.txt", "specs.txt"}
_REQ_SUFFIXES = {".txt", ".md"}


class GitHubCallbackBody(BaseModel):
    code: str
    state: str


class ImportBody(BaseModel):
    owner: str = Field(min_length=1, max_length=100)
    repo: str = Field(min_length=1, max_length=100)
    source_path: str = Field(min_length=1, max_length=500)
    requirements_path: str | None = Field(default=None, max_length=500)


def _require_repo_parts(owner: str, repo: str) -> tuple[str, str]:
    if not _REPO_NAME.fullmatch(owner) or not _REPO_NAME.fullmatch(repo):
        raise HTTPException(status_code=400, detail="Invalid repository name.")
    return owner, repo


def _safe_path(path: str) -> str:
    cleaned = path.replace("\\", "/").strip().lstrip("/")
    if not cleaned or ".." in cleaned.split("/"):
        raise HTTPException(status_code=400, detail="Invalid file path.")
    return cleaned


def _access_token(user: UserRecord) -> str:
    connection = get_github_connection(user.id)
    if not connection:
        raise HTTPException(status_code=400, detail="Connect GitHub first to browse repositories.")
    try:
        return decrypt_secret(connection.access_token_enc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Stored GitHub token is invalid. Reconnect GitHub.") from exc


def _decode_file_content(payload: dict[str, Any]) -> str:
    if payload.get("type") != "file":
        raise HTTPException(status_code=400, detail="That GitHub path is not a file.")
    size = int(payload.get("size") or 0)
    if size > _MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="File is too large to import (max 400 KB).")
    encoding = payload.get("encoding")
    content = payload.get("content") or ""
    if encoding == "base64":
        try:
            raw = base64.b64decode(content)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="Could not decode GitHub file.") from exc
    else:
        raw = str(content).encode("utf-8")
    if len(raw) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="File is too large to import (max 400 KB).")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File is not UTF-8 text.") from exc


@router.get("/url")
def github_auth_url(user: UserRecord = Depends(get_current_user)) -> dict[str, str]:
    try:
        url, state = create_github_auth_url(user.id)
        return {"url": url, "state": state}
    except GitHubOAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/callback")
def github_callback(
    body: GitHubCallbackBody,
    user: UserRecord = Depends(get_current_user),
) -> dict[str, Any]:
    owner_id = consume_github_state(body.state)
    if not owner_id or owner_id != user.id:
        raise HTTPException(status_code=400, detail="Invalid or expired GitHub OAuth state.")
    try:
        profile = exchange_code_for_github(body.code)
        upsert_github_connection(
            user_id=user.id,
            github_id=profile["github_id"],
            login=profile["login"],
            avatar_url=profile.get("avatar_url"),
            access_token_enc=encrypt_secret(profile["access_token"]),
            scope=profile.get("scope"),
        )
        return get_github_public(user.id)
    except GitHubOAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/status")
def github_status(user: UserRecord = Depends(get_current_user)) -> dict[str, Any]:
    return get_github_public(user.id)


@router.delete("/connection")
def github_disconnect(user: UserRecord = Depends(get_current_user)) -> dict[str, bool]:
    delete_github_connection(user.id)
    return {"disconnected": True}


@router.get("/repos")
def list_repos(
    page: int = 1,
    per_page: int = 30,
    user: UserRecord = Depends(get_current_user),
) -> dict[str, Any]:
    token = _access_token(user)
    page = max(1, page)
    per_page = min(max(per_page, 1), 100)
    try:
        items = github_request(
            token,
            "/user/repos",
            {
                "affiliation": "owner,collaborator,organization_member",
                "sort": "updated",
                "direction": "desc",
                "per_page": per_page,
                "page": page,
            },
        )
    except GitHubOAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    repos = [
        {
            "id": item.get("id"),
            "full_name": item.get("full_name"),
            "name": item.get("name"),
            "owner": (item.get("owner") or {}).get("login"),
            "private": bool(item.get("private")),
            "description": item.get("description"),
            "default_branch": item.get("default_branch"),
            "language": item.get("language"),
            "html_url": item.get("html_url"),
            "updated_at": item.get("updated_at"),
        }
        for item in items
        if isinstance(item, dict)
    ]
    return {"repos": repos, "page": page, "has_more": len(repos) == per_page}


@router.get("/contents")
def list_contents(
    owner: str,
    repo: str,
    path: str = "",
    user: UserRecord = Depends(get_current_user),
) -> dict[str, Any]:
    owner, repo = _require_repo_parts(owner, repo)
    token = _access_token(user)
    rel = path.replace("\\", "/").strip().lstrip("/")
    if rel and ".." in rel.split("/"):
        raise HTTPException(status_code=400, detail="Invalid file path.")
    api_path = f"/repos/{owner}/{repo}/contents"
    if rel:
        api_path = f"{api_path}/{rel}"
    try:
        payload = github_request(token, api_path)
    except GitHubOAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(payload, dict):
        payload = [payload]
    entries = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        kind = item.get("type")
        if kind == "dir":
            entries.append(
                {
                    "name": name,
                    "path": item.get("path"),
                    "type": "dir",
                }
            )
            continue
        lower = name.lower()
        is_source = any(lower.endswith(suffix) for suffix in _SOURCE_SUFFIXES)
        is_req = lower in _REQ_NAMES or any(lower.endswith(suffix) for suffix in _REQ_SUFFIXES)
        if not (is_source or is_req):
            continue
        entries.append(
            {
                "name": name,
                "path": item.get("path"),
                "type": "file",
                "size": item.get("size"),
                "kind": "source" if is_source else "requirements",
            }
        )
    entries.sort(key=lambda row: (0 if row["type"] == "dir" else 1, str(row["name"]).lower()))
    return {"owner": owner, "repo": repo, "path": rel, "entries": entries}


@router.post("/import")
def import_from_github(
    body: ImportBody,
    user: UserRecord = Depends(get_current_user),
) -> dict[str, str]:
    owner, repo = _require_repo_parts(body.owner, body.repo)
    source_path = _safe_path(body.source_path)
    if not source_path.lower().endswith(".py"):
        raise HTTPException(status_code=400, detail="Choose a Python (.py) source file.")
    token = _access_token(user)
    try:
        source_payload = github_request(token, f"/repos/{owner}/{repo}/contents/{source_path}")
    except GitHubOAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    source_code = _decode_file_content(source_payload)

    requirements_text = ""
    if body.requirements_path:
        req_path = _safe_path(body.requirements_path)
        try:
            req_payload = github_request(token, f"/repos/{owner}/{repo}/contents/{req_path}")
            requirements_text = _decode_file_content(req_payload)
        except GitHubOAuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "filename": source_path.split("/")[-1],
        "source_code": source_code,
        "requirements_text": requirements_text,
        "repo": f"{owner}/{repo}",
        "source_path": source_path,
    }
