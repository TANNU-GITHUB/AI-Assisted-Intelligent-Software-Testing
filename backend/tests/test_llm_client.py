import io

import httpx

from llm_client import (
    _public_llm_error,
    generate_from_image,
    generate_text,
    llm_is_configured,
    resolve_nvidia_model,
    resolve_nvidia_vision_model,
)


def test_public_llm_error_redacts_google_api_keys():
    api_key = "AIza" + ("A" * 35)
    assert api_key not in _public_llm_error(RuntimeError(f"request failed with {api_key}"))


def test_resolve_nvidia_model_default():
    model = resolve_nvidia_model()
    assert model
    assert "/" in model or model.isalnum()


def test_resolve_nvidia_vision_model_default(monkeypatch):
    monkeypatch.setattr(
        "llm_client.NVIDIA_VISION_MODEL",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    )
    assert (
        resolve_nvidia_vision_model()
        == "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    )
    assert resolve_nvidia_vision_model("custom/vision") == "custom/vision"


def test_resolve_nvidia_model_default_value():
    assert resolve_nvidia_model() == "nvidia/nemotron-3.5-lightning-30b-a3b"


def test_llm_is_configured_with_ollama_default():
    assert llm_is_configured() is True


def test_generate_from_image_uses_configured_nvidia_vision_model(monkeypatch):
    captured: dict = {}

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "If paid, then ship the order."}}]}

    class _Client:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json
            return _Response()

    monkeypatch.setattr("llm_client.NVIDIA_API_KEY", "test-vision-key")
    monkeypatch.setattr("llm_client.NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    monkeypatch.setattr(
        "llm_client.NVIDIA_VISION_MODEL",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    )
    monkeypatch.setattr("llm_client.httpx.Client", _Client)

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (64, 40), "white").save(buffer, format="PNG")

    text, provider = generate_from_image(buffer.getvalue(), "image/png", "Read this diagram.")

    assert text == "If paid, then ship the order."
    assert provider == "nvidia:nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer test-vision-key"
    body = captured["body"]
    assert body["model"] == "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    assert body["stream"] is False
    assert body["messages"][0] == {"role": "system", "content": "/no_think"}
    parts = body["messages"][1]["content"]
    assert parts[0]["type"] == "text"
    assert parts[1]["type"] == "image_url"
    assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_generate_from_image_retries_default_nvidia_model_after_410(monkeypatch):
    models = []

    class _Client:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers=None, json=None):
            del headers
            models.append(json["model"])
            request = httpx.Request("POST", url)
            if json["model"] == "old/vision-model":
                return httpx.Response(410, request=request)
            return httpx.Response(
                200,
                request=request,
                json={
                    "choices": [
                        {"message": {"content": "Diagram interpreted."}}
                    ]
                },
            )

    monkeypatch.setattr("llm_client.NVIDIA_API_KEY", "test-vision-key")
    monkeypatch.setattr("llm_client.NVIDIA_VISION_MODEL", "old/vision-model")
    monkeypatch.setattr("llm_client.httpx.Client", _Client)

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (64, 40), "white").save(buffer, format="PNG")

    text, provider = generate_from_image(
        buffer.getvalue(), "image/png", "Read this diagram."
    )

    assert text == "Diagram interpreted."
    assert provider == "nvidia:nvidia/nemotron-3.5-super-vl-120b-a12b"
    assert models == [
        "old/vision-model",
        "nvidia/nemotron-3.5-super-vl-120b-a12b",
    ]


def test_extract_openai_content_falls_back_to_reasoning_content():
    from llm_client import _extract_openai_content

    payload = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "reasoning_content": "Plan: extract scenarios.\nIf age >= 18, allow access.",
                }
            }
        ]
    }
    extracted = _extract_openai_content(payload)
    assert extracted == "Plan: extract scenarios.\nIf age >= 18, allow access."


def test_generate_text_retries_default_nvidia_model_after_410(monkeypatch):
    models = []

    class _Client:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers=None, json=None):
            del headers
            models.append(json["model"])
            request = httpx.Request("POST", url)
            if json["model"] == "old/text-model":
                return httpx.Response(410, request=request)
            return httpx.Response(
                200,
                request=request,
                json={
                    "choices": [
                        {"message": {"content": "Text processed."}}
                    ]
                },
            )

    monkeypatch.setattr("llm_client.NVIDIA_API_KEY", "test-text-key")
    monkeypatch.setattr("llm_client.NVIDIA_MODEL", "old/text-model")
    monkeypatch.setattr("llm_client.httpx.Client", _Client)

    text, provider = generate_text("Sample prompt.")

    assert text == "Text processed."
    assert provider == "nvidia:nvidia/nemotron-3.5-lightning-30b-a3b"
    assert models == [
        "old/text-model",
        "nvidia/nemotron-3.5-lightning-30b-a3b",
    ]
