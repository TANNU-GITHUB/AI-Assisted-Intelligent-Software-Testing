"""SQLite user persistence."""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from config import AUTH_DB_PATH


class AuthError(ValueError):
    pass


@dataclass
class UserRecord:
    id: str
    username: str
    email: str | None
    password_hash: str | None
    google_sub: str | None
    created_at: str

    def to_public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "auth_provider": "google" if self.google_sub else "local",
            "created_at": self.created_at,
        }


def _connect() -> sqlite3.Connection:
    AUTH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                email TEXT UNIQUE,
                password_hash TEXT,
                google_sub TEXT UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _row_to_user(row: sqlite3.Row) -> UserRecord:
    return UserRecord(
        id=row["id"],
        username=row["username"],
        email=row["email"],
        password_hash=row["password_hash"],
        google_sub=row["google_sub"],
        created_at=row["created_at"],
    )


def get_user_by_id(user_id: str) -> UserRecord | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_user(row) if row else None


def get_user_by_username(username: str) -> UserRecord | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username.strip(),)
        ).fetchone()
    return _row_to_user(row) if row else None


def get_user_by_google_sub(google_sub: str) -> UserRecord | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE google_sub = ?", (google_sub,)).fetchone()
    return _row_to_user(row) if row else None


def create_local_user(username: str, password_hash: str, email: str | None = None) -> UserRecord:
    username = username.strip()
    if get_user_by_username(username):
        raise AuthError("Username is already taken.")
    user_id = uuid.uuid4().hex
    created = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        try:
            conn.execute(
                """
                INSERT INTO users (id, username, email, password_hash, google_sub, created_at)
                VALUES (?, ?, ?, ?, NULL, ?)
                """,
                (user_id, username, email, password_hash, created),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise AuthError("Username or email is already registered.") from exc
    user = get_user_by_id(user_id)
    if not user:
        raise AuthError("Could not create user.")
    return user


def create_or_get_google_user(
    google_sub: str,
    email: str | None,
    suggested_username: str,
) -> UserRecord:
    existing = get_user_by_google_sub(google_sub)
    if existing:
        return existing
    base = _sanitize_username(suggested_username)
    username = _unique_username(base)
    user_id = uuid.uuid4().hex
    created = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO users (id, username, email, password_hash, google_sub, created_at)
            VALUES (?, ?, ?, NULL, ?, ?)
            """,
            (user_id, username, email, google_sub, created),
        )
        conn.commit()
    user = get_user_by_id(user_id)
    if not user:
        raise AuthError("Could not create Google user.")
    return user


def _sanitize_username(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value.lower())
    cleaned = cleaned.strip("_") or "user"
    return cleaned[:28]


def _unique_username(base: str) -> str:
    if not get_user_by_username(base):
        return base
    for index in range(2, 1000):
        candidate = f"{base}_{index}"
        if not get_user_by_username(candidate):
            return candidate
    raise AuthError("Could not allocate a unique username.")
