from llm_client import llm_is_configured, resolve_nvidia_model


def test_resolve_nvidia_model_default():
    model = resolve_nvidia_model()
    assert model
    assert "/" in model or model.isalnum()


def test_llm_is_configured_with_ollama_default():
    assert llm_is_configured() is True
