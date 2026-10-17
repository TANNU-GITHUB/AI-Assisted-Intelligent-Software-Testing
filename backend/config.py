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
NVIDIA_MODEL = (
    os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct").strip()
    or "meta/llama-3.3-70b-instruct"
)
NVIDIA_BASE_URL = (
    os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").strip()
    or "https://integrate.api.nvidia.com/v1"
)

# Fallback: local Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2").strip() or "llama3.2"

# Auth
AUTH_DB_PATH = ROOT_DIR / "data" / "auth.db"
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-use-long-random-string")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 7 days

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:3000/auth/google/callback"
).strip()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").strip()
