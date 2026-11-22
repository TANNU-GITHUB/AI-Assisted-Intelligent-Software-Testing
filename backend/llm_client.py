"""LLM client: NVIDIA NIM (primary) with local Ollama fallback."""

from __future__ import annotations

import base64
import io
import json
import re
import time
from typing import Any

import httpx

from config import (
    DEFAULT_NVIDIA_MODEL,
    DEFAULT_NVIDIA_VISION_MODEL,
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
    NVIDIA_MODEL,
    NVIDIA_VISION_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)

PLACEHOLDER_KEYS = frozenset(
    {
        "",
        "your_nvidia_api_key_here",
    }
)

HTTP_TIMEOUT = 90.0
CONNECT_TIMEOUT = 5.0


def _is_ollama_online(timeout: float = 0.5) -> bool:
    import socket
    import urllib.parse
    try:
        parsed = urllib.parse.urlparse(OLLAMA_BASE_URL)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 11434
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


class LLMError(RuntimeError):
    """Raised when all configured LLM providers fail."""


def resolve_nvidia_model(model_name: str | None = None) -> str:
    return (model_name or NVIDIA_MODEL or DEFAULT_NVIDIA_MODEL).strip()


def resolve_nvidia_vision_model(model_name: str | None = None) -> str:
    return (model_name or NVIDIA_VISION_MODEL or DEFAULT_NVIDIA_VISION_MODEL).strip()


_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_VISION_MAX_EDGE = 1536
_VISION_MAX_PIXELS = 40_000_000


def _public_llm_error(exc: Exception) -> str:
    text = str(exc)
    text = re.sub(r"Bearer\s+\S+", "Bearer [redacted]", text, flags=re.IGNORECASE)
    text = re.sub(r"nvapi-[A-Za-z0-9_\-]+", "[redacted]", text)
    text = re.sub(r"AIza[0-9A-Za-z_-]{30,}", "[redacted]", text)
    return text[:300]


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
    reasoning = message.get("reasoning_content")
    if isinstance(reasoning, str) and reasoning.strip():
        from json_utils import _FENCED_JSON
        match = _FENCED_JSON.search(reasoning)
        if match:
            return match.group(1).strip()
        return reasoning.strip()
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
        "max_tokens": 2048,
        "stream": False,
    }
    with httpx.Client(timeout=httpx.Timeout(HTTP_TIMEOUT, connect=CONNECT_TIMEOUT)) as client:
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
    with httpx.Client(timeout=httpx.Timeout(HTTP_TIMEOUT, connect=CONNECT_TIMEOUT)) as client:
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


def _prepare_vision_image(image_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
    """Return PNG bytes the Nemotron VL API can accept.

    The hosted model accepts PNG, JPEG, and WEBP, rejects an alpha channel,
    and tiles images in 512px blocks (at most 12 tiles). GIF uploads and
    PDF rasters are flattened and scaled before the request.
    """
    declared = (mime_type or "image").split(";")[0].strip().lower() or "image"
    if not image_bytes:
        raise LLMError(f"The {declared} image is empty.")
    try:
        from PIL import Image
    except ImportError as exc:
        raise LLMError(
            "Image support is not installed. Run: pip install Pillow"
        ) from exc

    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            width, height = image.size
            if width <= 0 or height <= 0 or width * height > _VISION_MAX_PIXELS:
                raise LLMError(
                    "Image dimensions are invalid or exceed the 40-megapixel limit."
                )
            if image.mode in {"RGBA", "LA", "P"}:
                rgba = image.convert("RGBA")
                background = Image.new("RGB", rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.getchannel("A"))
                prepared = background
            elif image.mode != "RGB":
                prepared = image.convert("RGB")
            else:
                prepared = image.copy()
    except LLMError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise LLMError(f"Could not read that {declared} image.") from exc

    width, height = prepared.size
    scale = min(_VISION_MAX_EDGE / max(width, 1), _VISION_MAX_EDGE / max(height, 1), 1)
    if scale < 1:
        prepared = prepared.resize(
            (max(32, int(width * scale)), max(32, int(height * scale))),
            Image.Resampling.LANCZOS,
        )
    if prepared.width < 32 or prepared.height < 32:
        prepared = prepared.resize(
            (max(prepared.width, 32), max(prepared.height, 32)),
            Image.Resampling.NEAREST,
        )
    buffer = io.BytesIO()
    prepared.save(buffer, format="PNG")
    return buffer.getvalue(), "image/png"


def _strip_thinking(text: str) -> str:
    return _THINK_BLOCK.sub("", text).strip()


def generate_from_image(
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    *,
    api_key: str | None = None,
    model_name: str | None = None,
    temperature: float = 0.2,
) -> tuple[str, str]:
    """Try NVIDIA, Gemini, then Ollama; return the response and provider label."""
    prepared, prepared_mime = _prepare_vision_image(image_bytes, mime_type)
    b64 = base64.b64encode(prepared).decode("ascii")
    data_url = f"data:{prepared_mime};base64,{b64}"
    nvidia_key = (api_key if api_key is not None else NVIDIA_API_KEY).strip()
    vision_model = resolve_nvidia_vision_model(model_name)
    errors: list[str] = []

    # NVIDIA NIM vision.
    if nvidia_key and nvidia_key not in PLACEHOLDER_KEYS:
        nvidia_models = [vision_model]
        if DEFAULT_NVIDIA_VISION_MODEL not in nvidia_models:
            nvidia_models.append(DEFAULT_NVIDIA_VISION_MODEL)
        if "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning" not in nvidia_models:
            nvidia_models.append("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")

        for candidate_model in nvidia_models:
            try:
                url = f"{NVIDIA_BASE_URL.rstrip('/')}/chat/completions"
                body = {
                    "model": candidate_model,
                    "messages": [
                        {"role": "system", "content": "/no_think"},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": data_url}},
                            ],
                        },
                    ],
                    "temperature": temperature,
                    "max_tokens": 4096,
                    "stream": False,
                }
                with httpx.Client(timeout=httpx.Timeout(HTTP_TIMEOUT, connect=CONNECT_TIMEOUT)) as client:
                    response = client.post(
                        url,
                        headers={
                            "Authorization": f"Bearer {nvidia_key}",
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                        },
                        json=body,
                    )
                    response.raise_for_status()
                    content = _strip_thinking(_extract_openai_content(response.json()))
                    if not content:
                        raise ValueError("NVIDIA vision model returned empty content.")
                    return content, f"nvidia:{candidate_model}"
            except httpx.HTTPStatusError as exc:
                errors.append(f"NVIDIA {candidate_model}: {_public_llm_error(exc)}")
                if (
                    exc.response.status_code in {404, 410}
                    and candidate_model != nvidia_models[-1]
                ):
                    continue
                break
            except Exception as exc:  # noqa: BLE001
                errors.append(f"NVIDIA {candidate_model}: {_public_llm_error(exc)}")
                break
    else:
        errors.append("NVIDIA: NVIDIA_API_KEY is not configured.")

    # Try Ollama llava fallback only if Ollama is online
    if _is_ollama_online():
        try:
            base = OLLAMA_BASE_URL.rstrip("/")
            body = {
                "model": "llava",
                "messages": [{"role": "user", "content": prompt, "images": [b64]}],
                "stream": False,
            }
            with httpx.Client(timeout=httpx.Timeout(HTTP_TIMEOUT, connect=CONNECT_TIMEOUT)) as client:
                response = client.post(f"{base}/api/chat", json=body)
                response.raise_for_status()
                data = response.json()
                text = _strip_thinking(str((data.get("message") or {}).get("content") or ""))
                if text:
                    return text, "ollama:llava"
                raise ValueError("Ollama llava returned empty content.")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Ollama llava: {_public_llm_error(exc)}")

    detail = "; ".join(errors) if errors else "No vision LLM configured."
    raise LLMError(
        f"Vision LLM request failed ({detail}). "
        "Set NVIDIA_API_KEY in backend/.env, or run Ollama locally "
        "with the llava model."
    )


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
        nvidia_models = [nvidia_model]
        if DEFAULT_NVIDIA_MODEL not in nvidia_models:
            nvidia_models.append(DEFAULT_NVIDIA_MODEL)
        if "nvidia/nemotron-3.5-lightning-30b-a3b" not in nvidia_models:
            nvidia_models.append("nvidia/nemotron-3.5-lightning-30b-a3b")
        if "mistralai/mistral-large-4-1t-a52b" not in nvidia_models:
            nvidia_models.append("mistralai/mistral-large-4-1t-a52b")

        for candidate in nvidia_models:
            try:
                text = _nvidia_chat(
                    full_prompt,
                    api_key=nvidia_key,
                    model=candidate,
                    temperature=temperature,
                )
                return text, f"nvidia:{candidate}"
            except httpx.HTTPStatusError as exc:
                errors.append(f"NVIDIA {candidate}: {_public_llm_error(exc)}")
                if (
                    exc.response.status_code in {404, 410}
                    and candidate != nvidia_models[-1]
                ):
                    continue
                break
            except Exception as exc:  # noqa: BLE001
                errors.append(f"NVIDIA {candidate}: {exc}")
                break

    if _is_ollama_online():
        ollama_model = (OLLAMA_MODEL or "llama3.2").strip()
        try:
            text = _ollama_chat(full_prompt, model=ollama_model, temperature=temperature)
            return text, f"ollama:{ollama_model}"
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Ollama: {exc}")
    else:
        ollama_model = (OLLAMA_MODEL or "llama3.2").strip()

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
