"""Shared configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

SESSIONS_DIR = ROOT_DIR / "sessions"
SCHEMA_VERSION = "1.0"

# Primary: NVIDIA NIM (OpenAI-compatible)
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
DEFAULT_NVIDIA_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
NVIDIA_MODEL = (
    os.getenv("NVIDIA_MODEL", DEFAULT_NVIDIA_MODEL).strip()
    or DEFAULT_NVIDIA_MODEL
)
NVIDIA_BASE_URL = (
    os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").strip()
    or "https://integrate.api.nvidia.com/v1"
)
DEFAULT_NVIDIA_VISION_MODEL = "nvidia/nemotron-3.5-super-vl-120b-a12b"
# Vision: NVIDIA Nemotron 3.5 Super VL (OpenAI-compatible chat completions).
# https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b
NVIDIA_VISION_MODEL = (
    os.getenv("NVIDIA_VISION_MODEL", DEFAULT_NVIDIA_VISION_MODEL).strip()
    or DEFAULT_NVIDIA_VISION_MODEL
)

# Fallback: local Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2").strip() or "llama3.2"

# Auth
AUTH_DB_PATH = ROOT_DIR / "data" / "auth.db"
_JWT_UNSAFE_VALUES = {
    "change-me-in-production-use-long-random-string",
    "generate-a-long-random-secret-for-production",
}
JWT_SECRET = os.getenv("JWT_SECRET", "").strip()
if not JWT_SECRET or JWT_SECRET in _JWT_UNSAFE_VALUES:
    raise RuntimeError(
        "JWT_SECRET must be set to a strong, persistent random secret. "
        "Generate one with: python -c "
        "\"import secrets; print(secrets.token_hex(32))\""
    )
if len(JWT_SECRET.encode("utf-8")) < 32:
    raise RuntimeError(
        "JWT_SECRET must be at least 32 bytes. "
        "Generate one with: python -c "
        "\"import secrets; print(secrets.token_hex(32))\""
    )
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 7 days

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:3000/auth/google/callback"
).strip()
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "").strip()
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "").strip()
GITHUB_REDIRECT_URI = os.getenv(
    "GITHUB_REDIRECT_URI", "http://localhost:3000/auth/github/callback"
).strip()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").strip()
