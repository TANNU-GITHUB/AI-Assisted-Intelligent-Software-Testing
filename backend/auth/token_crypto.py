"""Encrypt OAuth access tokens at rest using JWT_SECRET."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

from config import JWT_SECRET


def _key() -> bytes:
    return hashlib.sha256(f"oauth-token:{JWT_SECRET}".encode("utf-8")).digest()


def encrypt_secret(plain: str) -> str:
    key = _key()
    nonce = os.urandom(16)
    data = plain.encode("utf-8")
    stream = hashlib.sha256(key + nonce).digest()
    cipher = bytes(b ^ stream[i % len(stream)] for i, b in enumerate(data))
    mac = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(nonce + mac + cipher).decode("ascii")


def decrypt_secret(blob: str) -> str:
    key = _key()
    raw = base64.urlsafe_b64decode(blob.encode("ascii"))
    if len(raw) < 49:
        raise ValueError("Invalid encrypted token.")
    nonce, mac, cipher = raw[:16], raw[16:48], raw[48:]
    expected = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise ValueError("Token integrity check failed.")
    stream = hashlib.sha256(key + nonce).digest()
    plain = bytes(b ^ stream[i % len(stream)] for i, b in enumerate(cipher))
    return plain.decode("utf-8")
