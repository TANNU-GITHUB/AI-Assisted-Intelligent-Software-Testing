"""Ensure authenticated users only access their own sessions."""

from __future__ import annotations

from fastapi import HTTPException

from auth.store import UserRecord
from input_handler.handler import load_session


def assert_session_owner(session_id: str, user: UserRecord) -> None:
    payload = load_session(session_id)
    owner = payload.get("owner_user_id")
    if owner and owner != user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this session.")
