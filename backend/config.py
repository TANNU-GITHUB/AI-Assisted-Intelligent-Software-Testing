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
