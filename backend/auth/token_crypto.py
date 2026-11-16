"""Encrypt OAuth access tokens at rest."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.fernet import Fernet, InvalidToken

from config import JWT_SECRET

_FERNET_VERSION = 0x80


def _key_material() -> bytes:
    return hashlib.sha256(f"oauth-token:{JWT_SECRET}".encode("utf-8")).digest()


def _key() -> bytes:
    return base64.urlsafe_b64encode(_key_material())


def _fernet() -> Fernet:
    return Fernet(_key())


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def _decrypt_legacy_secret(blob: str) -> str:
    # Read old records only so startup can migrate them; new writes use Fernet.
    try:
        raw = base64.urlsafe_b64decode(blob.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise ValueError("Invalid encrypted token.") from exc
    if len(raw) < 49:
        raise ValueError("Invalid encrypted token.")

    nonce, mac, cipher = raw[:16], raw[16:48], raw[48:]
    key = _key_material()
    expected = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise ValueError("Token integrity check failed.")

    stream = hashlib.sha256(key + nonce).digest()
    plain = bytes(b ^ stream[i % len(stream)] for i, b in enumerate(cipher))
    try:
        return plain.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Invalid encrypted token.") from exc


def decrypt_secret_with_upgrade(blob: str) -> tuple[str, str | None]:
    try:
        raw = base64.urlsafe_b64decode(blob.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise ValueError("Invalid encrypted token.") from exc

    if raw[:1] == bytes([_FERNET_VERSION]):
        try:
            return _fernet().decrypt(blob.encode("ascii")).decode("utf-8"), None
        except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
            raise ValueError("Invalid encrypted token.") from exc

    plain = _decrypt_legacy_secret(blob)
    return plain, encrypt_secret(plain)


def decrypt_secret(blob: str) -> str:
    plain, _replacement = decrypt_secret_with_upgrade(blob)
    return plain
