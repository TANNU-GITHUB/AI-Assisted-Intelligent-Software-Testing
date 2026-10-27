"""GitHub OAuth 2.0 — connect an existing account to list and read the user's repos."""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlencode

import httpx

from config import GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_REDIRECT_URI

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API = "https://api.github.com"
GITHUB_SCOPES = "read:user repo"

_pending_states: dict[str, str] = {}


class GitHubOAuthError(RuntimeError):
    pass


def create_github_auth_url(user_id: str) -> tuple[str, str]:
    if not GITHUB_CLIENT_ID or not GITHUB_REDIRECT_URI:
        raise GitHubOAuthError(
            "GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_REDIRECT_URI."
        )
    state = secrets.token_urlsafe(24)
    _pending_states[state] = user_id
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": GITHUB_SCOPES,
        "state": state,
        "allow_signup": "false",
    }
    return f"{GITHUB_AUTH_URL}?{urlencode(params)}", state


def consume_github_state(state: str) -> str | None:
    return _pending_states.pop(state, None)


def exchange_code_for_github(code: str) -> dict[str, Any]:
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET or not GITHUB_REDIRECT_URI:
        raise GitHubOAuthError("GitHub OAuth is not configured on the server.")
    with httpx.Client(timeout=30.0) as client:
        token_res = client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_REDIRECT_URI,
            },
        )
        if token_res.status_code >= 400:
            raise GitHubOAuthError(f"GitHub token exchange failed: {token_res.text}")
        tokens = token_res.json()
        access_token = tokens.get("access_token")
        if not access_token:
            raise GitHubOAuthError(
                tokens.get("error_description") or "GitHub did not return an access token."
            )
        profile_res = client.get(
            f"{GITHUB_API}/user",
            headers=_github_headers(access_token),
        )
        if profile_res.status_code >= 400:
            raise GitHubOAuthError("Could not load GitHub profile.")
        profile = profile_res.json()
    github_id = profile.get("id")
    login = profile.get("login")
    if github_id is None or not login:
        raise GitHubOAuthError("GitHub profile missing id or login.")
    return {
        "github_id": str(github_id),
        "login": login,
        "avatar_url": profile.get("avatar_url"),
        "access_token": access_token,
        "scope": tokens.get("scope") or GITHUB_SCOPES,
    }


def _github_headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "bugai-testing-lab",
    }


def decode_github_file(payload: dict[str, Any], *, max_bytes: int = 400_000) -> str:
    import base64

    if payload.get("type") != "file":
        raise GitHubOAuthError("That GitHub path is not a file.")
    size = int(payload.get("size") or 0)
    if size > max_bytes:
        raise GitHubOAuthError(f"File is too large to import (max {max_bytes} bytes).")
    encoding = payload.get("encoding")
    content = payload.get("content") or ""
    if encoding == "base64":
        try:
            raw = base64.b64decode(content)
        except Exception as exc:  # noqa: BLE001
            raise GitHubOAuthError("Could not decode GitHub file.") from exc
    else:
        raw = str(content).encode("utf-8")
    if len(raw) > max_bytes:
        raise GitHubOAuthError(f"File is too large to import (max {max_bytes} bytes).")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GitHubOAuthError("File is not UTF-8 text.") from exc


def github_request(access_token: str, path: str, params: dict[str, Any] | None = None) -> Any:
    with httpx.Client(timeout=45.0) as client:
        res = client.get(
            f"{GITHUB_API}{path}",
            headers=_github_headers(access_token),
            params=params or {},
        )
    if res.status_code == 401:
        raise GitHubOAuthError("GitHub access expired. Reconnect your GitHub account.")
    if res.status_code == 403:
        raise GitHubOAuthError("GitHub rate limit or permission denied for this repository.")
    if res.status_code == 404:
        raise GitHubOAuthError("Repository or file not found, or you do not have access.")
    if res.status_code >= 400:
        raise GitHubOAuthError(f"GitHub API error ({res.status_code}).")
    return res.json()
