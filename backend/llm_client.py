"""LLM client: NVIDIA NIM (primary) with local Ollama fallback.

Fallback order: NVIDIA NIM → Ollama (if running) → LLMError
When neither is reachable, callers receive a clear LLMError rather than a
raw 500. All public functions are safe to call even when both providers are
offline — they raise LLMError, which is caught by the FastAPI exception
handler and surfaced as HTTP 503.
"""

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
NVIDIA_HTTP_TIMEOUT = 20.0
OLLAMA_HTTP_TIMEOUT = 45.0
CONNECT_TIMEOUT = 3.0
NVIDIA_PROMPT_CHARS = 16_000
OLLAMA_PROMPT_CHARS = 6_000
NVIDIA_QUOTA_COOLDOWN = 1800.0
NVIDIA_TRANSIENT_COOLDOWN = 180.0

_EXHAUSTED_STATUS_CODES = frozenset({401, 402, 403, 429})
_EXHAUSTED_MARKERS = (
    "quota",
    "rate limit",
    "rate_limit",
    "ratelimit",
    "too many requests",
    "insufficient_quota",
    "insufficient credit",
    "out of credit",
    "out of credits",
    "billing",
    "resource has been exhausted",
    "exceeded your current quota",
    "credit balance",
)
_CONTEXT_MARKERS = (
    "context length",
    "maximum context",
    "too many tokens",
    "prompt is too long",
    "context window",
    "max context",
)


def _is_ollama_online(timeout: float = 1.5) -> bool:
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


def _resolve_available_ollama_model(preferred: str = "llama3.2:1b") -> str:
    try:
        base = OLLAMA_BASE_URL.rstrip("/")
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{base}/api/tags")
            if resp.status_code == 200:
                models = [m.get("name", "") for m in resp.json().get("models", [])]
                # Exact match first
                if preferred in models:
                    return preferred
                # If :tag omitted or matches with tag
                for m in models:
                    if m == preferred or m.startswith(f"{preferred}:"):
                        return m
                # Substring match
                for m in models:
                    if preferred in m or m.startswith(preferred):
                        return m
                # If preferred was llama3.2:1b but llama3.2:latest is present, or vice-versa
                for m in models:
                    if "llama3.2" in m:
                        return m
                if models:
                    return models[0]
    except Exception:
        pass
    return preferred


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


def _clip_prompt(prompt: str, max_chars: int) -> str:
    if max_chars <= 0 or len(prompt) <= max_chars:
        return prompt
    keep = max(256, (max_chars - 40) // 2)
    return f"{prompt[:keep]}\n\n# ... (truncated for model context) ...\n\n{prompt[-keep:]}"


def _http_error_body(exc: httpx.HTTPStatusError) -> str:
    try:
        return (exc.response.text or "")[:800]
    except Exception:
        return ""


def _combined_error_text(exc: BaseException) -> str:
    body = _http_error_body(exc) if isinstance(exc, httpx.HTTPStatusError) else ""
    return f"{exc} {body}".lower()


def _is_nvidia_quota_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in _EXHAUSTED_STATUS_CODES:
        return True
    text = _combined_error_text(exc)
    return any(marker in text for marker in _EXHAUSTED_MARKERS)


def _is_nvidia_context_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {413, 422}:
        return True
    text = _combined_error_text(exc)
    return any(marker in text for marker in _CONTEXT_MARKERS)


def _is_nvidia_unavailable(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {500, 502, 503, 504}:
        return True
    return False


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
    max_chars: int = NVIDIA_PROMPT_CHARS,
) -> str:
    url = f"{NVIDIA_BASE_URL.rstrip('/')}/chat/completions"
    clipped = _clip_prompt(prompt, max_chars)
    body = {
        "model": model,
        "messages": [{"role": "user", "content": clipped}],
        "temperature": temperature,
        "max_tokens": 2048,
        "stream": False,
    }
    timeout = httpx.Timeout(NVIDIA_HTTP_TIMEOUT, connect=CONNECT_TIMEOUT)
    with httpx.Client(timeout=timeout) as client:
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


_NVIDIA_EXHAUSTED_UNTIL = 0.0


def mark_nvidia_exhausted(duration_seconds: float = NVIDIA_QUOTA_COOLDOWN) -> None:
    global _NVIDIA_EXHAUSTED_UNTIL
    _NVIDIA_EXHAUSTED_UNTIL = time.time() + max(duration_seconds, 1.0)


def clear_nvidia_exhausted() -> None:
    global _NVIDIA_EXHAUSTED_UNTIL
    _NVIDIA_EXHAUSTED_UNTIL = 0.0


def is_nvidia_exhausted() -> bool:
    return time.time() < _NVIDIA_EXHAUSTED_UNTIL


def _ollama_chat(
    prompt: str,
    *,
    model: str,
    temperature: float,
    want_json: bool = True,
    max_chars: int = OLLAMA_PROMPT_CHARS,
) -> str:
    base = OLLAMA_BASE_URL.rstrip("/")
    clipped = _clip_prompt(prompt, max_chars)
    timeout = httpx.Timeout(OLLAMA_HTTP_TIMEOUT, connect=CONNECT_TIMEOUT)
    native_url = f"{base}/api/chat"
    native_body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": clipped}],
        "stream": False,
        "options": {"temperature": temperature, "num_predict": 2048},
    }
    # Strict JSON mode is unreliable on small local models with large prompts.
    if want_json and len(clipped) < 4000:
        native_body["format"] = "json"

    with httpx.Client(timeout=timeout) as client:
        try:
            response = client.post(native_url, json=native_body)
            response.raise_for_status()
            data = response.json()
            text = (data.get("message") or {}).get("content")
            if text and str(text).strip():
                return str(text).strip()
        except Exception:
            pass

        openai_url = f"{base}/v1/chat/completions"
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": clipped}],
            "temperature": temperature,
            "stream": False,
        }
        try:
            response = client.post(openai_url, json=body)
            response.raise_for_status()
            return _extract_openai_content(response.json())
        except Exception as exc:
            raise ValueError(f"Ollama chat generation failed for model '{model}': {exc}") from exc


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
    nvidia_available = (
        nvidia_key
        and nvidia_key not in PLACEHOLDER_KEYS
        and not is_nvidia_exhausted()
    )
    if nvidia_available:
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
                if _is_nvidia_quota_error(exc):
                    mark_nvidia_exhausted(NVIDIA_QUOTA_COOLDOWN)
                    break
                if (
                    exc.response.status_code in {404, 410}
                    and candidate_model != nvidia_models[-1]
                ):
                    continue
                break
            except Exception as exc:  # noqa: BLE001
                errors.append(f"NVIDIA {candidate_model}: {_public_llm_error(exc)}")
                if _is_nvidia_quota_error(exc) or _is_nvidia_unavailable(exc):
                    mark_nvidia_exhausted(NVIDIA_TRANSIENT_COOLDOWN)
                break
    else:
        errors.append("NVIDIA: NVIDIA_API_KEY is not configured or quota is exhausted.")

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
    Tries NVIDIA NIM first, then local Ollama for the rest of the run
    when the NVIDIA key is exhausted, rate-limited, or otherwise unavailable.
    """
    full_prompt = _json_hint(prompt, response_mime_type)
    nvidia_key = (api_key if api_key is not None else NVIDIA_API_KEY).strip()
    nvidia_model = resolve_nvidia_model(model_name)
    errors: list[str] = []

    nvidia_available = (
        nvidia_key
        and nvidia_key not in PLACEHOLDER_KEYS
        and not is_nvidia_exhausted()
    )

    if nvidia_available:
        nvidia_models = [nvidia_model]
        if DEFAULT_NVIDIA_MODEL not in nvidia_models:
            nvidia_models.append(DEFAULT_NVIDIA_MODEL)

        nvidia_char_limits = (NVIDIA_PROMPT_CHARS, 8_000, 4_000)
        stop_nvidia = False
        for candidate in nvidia_models:
            try_next_model = False
            for limit in nvidia_char_limits:
                try:
                    text = _nvidia_chat(
                        full_prompt,
                        api_key=nvidia_key,
                        model=candidate,
                        temperature=temperature,
                        max_chars=limit,
                    )
                    return text, f"nvidia:{candidate}"
                except httpx.HTTPStatusError as exc:
                    errors.append(f"NVIDIA {candidate}: {_public_llm_error(exc)}")
                    if _is_nvidia_quota_error(exc):
                        mark_nvidia_exhausted(NVIDIA_QUOTA_COOLDOWN)
                        stop_nvidia = True
                        break
                    if _is_nvidia_context_error(exc):
                        continue
                    if _is_nvidia_unavailable(exc):
                        mark_nvidia_exhausted(NVIDIA_TRANSIENT_COOLDOWN)
                        stop_nvidia = True
                        break
                    if (
                        exc.response.status_code in {404, 410}
                        and candidate != nvidia_models[-1]
                    ):
                        try_next_model = True
                        break
                    stop_nvidia = True
                    break
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"NVIDIA {candidate}: {exc}")
                    if _is_nvidia_quota_error(exc):
                        mark_nvidia_exhausted(NVIDIA_QUOTA_COOLDOWN)
                        stop_nvidia = True
                        break
                    if _is_nvidia_context_error(exc):
                        continue
                    if _is_nvidia_unavailable(exc):
                        mark_nvidia_exhausted(NVIDIA_TRANSIENT_COOLDOWN)
                    stop_nvidia = True
                    break
            if stop_nvidia:
                break
            if try_next_model:
                continue
            # Context window still too large after shrinking; let Ollama finish.
            break

    ollama_model = _resolve_available_ollama_model((OLLAMA_MODEL or "llama3.2").strip())
    if _is_ollama_online():
        ollama_limits = (OLLAMA_PROMPT_CHARS, 4_000, 2_000)
        for limit in ollama_limits:
            try:
                text = _ollama_chat(
                    full_prompt,
                    model=ollama_model,
                    temperature=temperature,
                    want_json=response_mime_type == "application/json",
                    max_chars=limit,
                )
                return text, f"ollama:{ollama_model}"
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Ollama ({ollama_model}): {exc}")
                if not (_is_nvidia_context_error(exc) or _is_nvidia_unavailable(exc)):
                    break
    else:
        errors.append(
            f"Ollama is not running at {OLLAMA_BASE_URL}. "
            "Start Ollama so remaining work can continue after NVIDIA quota is used."
        )

    detail = "; ".join(errors) if errors else "No LLM configured."
    raise LLMError(
        f"LLM request failed ({detail}). "
        "Set NVIDIA_API_KEY in backend/.env or run Ollama locally "
        f"({OLLAMA_BASE_URL}, model {ollama_model})."
    )


def llm_is_configured() -> bool:
    key = NVIDIA_API_KEY.strip()
    if key and key not in PLACEHOLDER_KEYS and not is_nvidia_exhausted():
        return True
    return _is_ollama_online()
