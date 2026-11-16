import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
CONFIG_IMPORT = "import config; print(config.JWT_SECRET)"


def _import_config_with_secret(secret: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["JWT_SECRET"] = secret
    return subprocess.run(
        [sys.executable, "-c", CONFIG_IMPORT],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("secret", "error"),
    [
        ("", "JWT_SECRET must be set"),
        (
            "change-me-in-production-use-long-random-string",
            "JWT_SECRET must be set",
        ),
        (
            "generate-a-long-random-secret-for-production",
            "JWT_SECRET must be set",
        ),
        ("too-short", "JWT_SECRET must be at least 32 bytes"),
    ],
)
def test_config_refuses_missing_default_and_short_jwt_secrets(secret: str, error: str):
    result = _import_config_with_secret(secret)

    assert result.returncode != 0
    assert error in result.stderr


def test_config_accepts_a_persistent_random_jwt_secret():
    secret = secrets.token_hex(32)

    result = _import_config_with_secret(secret)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == secret
