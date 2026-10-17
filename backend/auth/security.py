"""Password hashing and JWT tokens."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,32}$")


class AuthValidationError(ValueError):
    pass


def validate_username(username: str) -> str:
    name = username.strip()
    if not USERNAME_PATTERN.fullmatch(name):
        raise AuthValidationError(
            "Username must be 3–32 characters and use only letters, numbers, or underscores."
        )
    return name


def validate_password(password: str) -> None:
    if len(password) < 8:
        raise AuthValidationError("Password must be at least 8 characters.")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "username": username,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise AuthValidationError("Invalid or expired token.") from exc
