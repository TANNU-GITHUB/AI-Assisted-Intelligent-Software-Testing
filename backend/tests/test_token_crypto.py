import base64
import hashlib
import hmac
import os

import pytest

from auth.token_crypto import (
    decrypt_secret,
    decrypt_secret_with_upgrade,
    encrypt_secret,
)
from config import JWT_SECRET


def _legacy_encrypt(plain: str) -> str:
    key = hashlib.sha256(f"oauth-token:{JWT_SECRET}".encode("utf-8")).digest()
    nonce = os.urandom(16)
    data = plain.encode("utf-8")
    stream = hashlib.sha256(key + nonce).digest()
    cipher = bytes(byte ^ stream[index % len(stream)] for index, byte in enumerate(data))
    mac = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(nonce + mac + cipher).decode("ascii")


def test_fernet_encrypts_and_decrypts_long_oauth_tokens():
    token = "gho_" + "a" * 100

    encrypted = encrypt_secret(token)

    assert encrypted.startswith("gAAAA")
    assert encrypted != token
    assert decrypt_secret(encrypted) == token


def test_legacy_token_is_decrypted_and_upgraded_to_fernet():
    token = "gho_" + "legacy-token-" * 8
    legacy_blob = _legacy_encrypt(token)

    decrypted, upgraded = decrypt_secret_with_upgrade(legacy_blob)

    assert decrypted == token
    assert upgraded is not None
    assert upgraded.startswith("gAAAA")
    assert decrypt_secret(upgraded) == token


def test_invalid_or_tampered_tokens_are_rejected():
    encrypted = encrypt_secret("gho_test-token")
    tampered = encrypted[:-4] + "AAAA"

    with pytest.raises(ValueError, match="Invalid encrypted token"):
        decrypt_secret(tampered)

    with pytest.raises(ValueError):
        decrypt_secret("not-a-valid-token")
