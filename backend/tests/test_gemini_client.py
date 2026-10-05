from gemini_client import resolve_gemini_model


def test_legacy_model_is_remapped():
    assert resolve_gemini_model("gemini-2.0-flash") == "gemini-2.5-flash"
