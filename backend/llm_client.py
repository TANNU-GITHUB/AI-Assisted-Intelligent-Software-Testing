"""LLM client: NVIDIA NIM (primary) with local Ollama fallback."""

from __future__ import annotations

import json
from typing import Any

import httpx

from config import (
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
    NVIDIA_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)

PLACEHOLDER_KEYS = frozenset(
    {
        "",
        "your_nvidia_api_key_here",
    }
)

HTTP_TIMEOUT = 120.0


class LLMError(RuntimeError):
    """Raised when NVIDIA and Ollama both fail."""


def resolve_nvidia_model(model_name: str | None = None) -> str:
    return (model_name or NVIDIA_MODEL or "meta/llama-3.3-70b-instruct").strip()


def _json_hint(prompt: str, response_mime_type: str) -> str:
    if response_mime_type != "application/json":
        return prompt
    return (
        prompt
        + "\n\nRespond with valid JSON only. No markdown fences, no commentary."
    )


def _extract_openai_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("LLM returned no choices.")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        text = "".join(parts).strip()
        if text:
            return text
    raise ValueError("LLM returned empty content.")


def _nvidia_chat(
    prompt: str,
    *,
    api_key: str,
    model: str,
    temperature: float,
) -> str:
    url = f"{NVIDIA_BASE_URL.rstrip('/')}/chat/completions"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 4096,
        "stream": False,
    }
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        response = client.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        response.raise_for_status()
        return _extract_openai_content(response.json())


def _ollama_chat(prompt: str, *, model: str, temperature: float) -> str:
    base = OLLAMA_BASE_URL.rstrip("/")
    openai_url = f"{base}/v1/chat/completions"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "stream": False,
    }
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        try:
            response = client.post(openai_url, json=body)
            if response.status_code == 404:
                raise httpx.HTTPStatusError(
                    "Ollama OpenAI route missing", request=response.request, response=response
                )
            response.raise_for_status()
            return _extract_openai_content(response.json())
        except (httpx.HTTPError, ValueError, json.JSONDecodeError):
            native_url = f"{base}/api/chat"
            native_body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": temperature},
            }
            response = client.post(native_url, json=native_body)
            response.raise_for_status()
            data = response.json()
            text = (data.get("message") or {}).get("content")
            if not text or not str(text).strip():
                raise ValueError("Ollama returned empty content.")
            return str(text).strip()


def generate_text(
    prompt: str,
    *,
    api_key: str | None = None,
    model_name: str | None = None,
    response_mime_type: str = "application/json",
    temperature: float = 0.2,
) -> tuple[str, str]:
    """
    Return (text, provider_label).
    Tries NVIDIA NIM first, then Ollama on any failure.
    """
    full_prompt = _json_hint(prompt, response_mime_type)
    nvidia_key = (api_key if api_key is not None else NVIDIA_API_KEY).strip()
    nvidia_model = resolve_nvidia_model(model_name)
    errors: list[str] = []

    if nvidia_key and nvidia_key not in PLACEHOLDER_KEYS:
        try:
            text = _nvidia_chat(
                full_prompt,
                api_key=nvidia_key,
                model=nvidia_model,
                temperature=temperature,
            )
            return text, f"nvidia:{nvidia_model}"
        except Exception as exc:  # noqa: BLE001
            errors.append(f"NVIDIA: {exc}")

    ollama_model = (OLLAMA_MODEL or "llama3.2").strip()
    try:
        text = _ollama_chat(full_prompt, model=ollama_model, temperature=temperature)
        return text, f"ollama:{ollama_model}"
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Ollama: {exc}")

    detail = "; ".join(errors) if errors else "No LLM configured."
    raise LLMError(
        f"LLM request failed ({detail}). "
        "Set NVIDIA_API_KEY in backend/.env or run Ollama locally "
        f"({OLLAMA_BASE_URL}, model {ollama_model})."
    )


def llm_is_configured() -> bool:
    key = NVIDIA_API_KEY.strip()
    if key and key not in PLACEHOLDER_KEYS:
        return True
    return bool(OLLAMA_BASE_URL.strip())
