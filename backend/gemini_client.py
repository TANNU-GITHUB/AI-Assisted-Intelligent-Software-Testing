"""Shared Gemini client helpers (google-genai SDK)."""

from __future__ import annotations

from config import GEMINI_MODEL

LEGACY_MODEL_ALIASES = {
    "gemini-2.0-flash": "gemini-2.5-flash",
    "models/gemini-2.0-flash": "gemini-2.5-flash",
}

FALLBACK_MODELS = (
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview",
)

TRANSIENT_HTTP_CODES = frozenset({429, 502, 503, 504})
MAX_ATTEMPTS_PER_MODEL = 1
HTTP_TIMEOUT_MS = 12_000


def resolve_gemini_model(model_name: str | None = None) -> str:
    model = (model_name or GEMINI_MODEL or "gemini-2.5-flash").strip()
    if model.startswith("models/"):
        model = model.removeprefix("models/")
    return LEGACY_MODEL_ALIASES.get(model, model)


def _model_candidates(preferred: str | None = None) -> list[str]:
    primary = resolve_gemini_model(preferred)
    candidates: list[str] = [primary]
    for model in FALLBACK_MODELS:
        if model not in candidates:
            candidates.append(model)
    return candidates


def _api_error_code(exc: Exception) -> int | None:
    for attr in ("code", "status_code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    message = str(exc)
    for code in (404, 429, 502, 503, 504):
        if str(code) in message:
            return code
    if "NOT_FOUND" in message or "no longer available" in message:
        return 404
    if "UNAVAILABLE" in message or "high demand" in message.lower():
        return 503
    return None


def _is_model_not_found(exc: Exception, code: int | None) -> bool:
    message = str(exc)
    return code == 404 or "NOT_FOUND" in message or "no longer available" in message


def _is_transient_error(exc: Exception, code: int | None) -> bool:
    if code in TRANSIENT_HTTP_CODES:
        return True
    message = str(exc).lower()
    return "unavailable" in message or "high demand" in message or "rate limit" in message


def generate_text(
    prompt: str,
    *,
    api_key: str,
    model_name: str | None = None,
    response_mime_type: str = "application/json",
    temperature: float = 0.2,
) -> tuple[str, str]:
    """Return (text, model_used). Retries transient errors and tries fallback models."""
    from google import genai
    from google.genai import errors as genai_errors
    from google.genai import types

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=HTTP_TIMEOUT_MS),
    )
    config = types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type=response_mime_type,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    last_error: Exception | None = None
    for model in _model_candidates(model_name):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            text = (response.text or "").strip()
            if not text:
                raise ValueError("Gemini returned an empty response.")
            return text, model
        except (genai_errors.ClientError, genai_errors.ServerError) as exc:
            last_error = exc
            code = _api_error_code(exc)
            if _is_model_not_found(exc, code):
                continue
            # Fail fast on 503/429 so callers can use local fallbacks
            # instead of hanging the Live Lab proxy until it returns 500.
            raise
        except ValueError as exc:
            last_error = exc
            raise

    if last_error is not None:
        raise last_error
    raise RuntimeError("Gemini request failed with no available model.")
