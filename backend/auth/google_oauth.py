"""Google OAuth 2.0 authorization code flow."""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlencode

import httpx

from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

# In-memory OAuth state (dev); use Redis in production multi-instance setups.
_pending_states: set[str] = set()


class GoogleOAuthError(RuntimeError):
    pass


def create_google_auth_url() -> tuple[str, str]:
    if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
        raise GoogleOAuthError(
            "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_REDIRECT_URI."
        )
    state = secrets.token_urlsafe(24)
    _pending_states.add(state)
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}", state


def consume_oauth_state(state: str) -> bool:
    if state in _pending_states:
        _pending_states.discard(state)
        return True
    return False


def exchange_code_for_user(code: str) -> dict[str, Any]:
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not GOOGLE_REDIRECT_URI:
        raise GoogleOAuthError("Google OAuth is not configured on the server.")
    with httpx.Client(timeout=30.0) as client:
        token_res = client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if token_res.status_code >= 400:
            raise GoogleOAuthError(f"Google token exchange failed: {token_res.text}")
        tokens = token_res.json()
        access_token = tokens.get("access_token")
        if not access_token:
            raise GoogleOAuthError("Google did not return an access token.")
        profile_res = client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if profile_res.status_code >= 400:
            raise GoogleOAuthError("Could not load Google profile.")
        profile = profile_res.json()
    sub = profile.get("sub")
    if not sub:
        raise GoogleOAuthError("Google profile missing subject id.")
    email = profile.get("email")
    name = profile.get("name") or email or "google_user"
    return {"sub": sub, "email": email, "name": name}
