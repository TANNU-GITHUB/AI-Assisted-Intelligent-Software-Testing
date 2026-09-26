import json

import pytest

from requirement_analysis.analyzer import RequirementAnalysisError, analyze_requirements


VALID_JSON = json.dumps(
    {
        "requirements": [
            {
                "requirement_id": "REQ-01",
                "condition": "is_member is True",
                "expected_result": "10 percent discount is applied",
                "source_excerpt": "Members receive a 10% discount",
            },
            {
                "requirement_id": "REQ-02",
                "condition": "price is negative",
                "expected_result": "an error is raised",
                "source_excerpt": "Negative prices must be rejected",
            },
        ]
    }
)


def test_parses_valid_llm_json():
    result = analyze_requirements(
        "Members receive a 10% discount. Negative prices must be rejected.",
        api_key="test-key",
        llm_call=lambda prompt, key, model: VALID_JSON,
    )
    assert result["requirement_count"] == 2
    assert result["requirements"][0]["requirement_id"] == "REQ-01"
    assert "discount" in result["requirements"][0]["expected_result"]


def test_retries_when_first_response_is_not_json():
    calls = {"n": 0}

    def flaky(prompt, key, model):
        calls["n"] += 1
        if calls["n"] == 1:
            return "sorry, here is some prose"
        return VALID_JSON

    result = analyze_requirements(
        "Members receive a 10% discount.",
        api_key="test-key",
        llm_call=flaky,
    )
    assert calls["n"] == 2
    assert result["requirement_count"] == 2


def test_fails_after_retry():
    with pytest.raises(RequirementAnalysisError, match="retry"):
        analyze_requirements(
            "Anything",
            api_key="test-key",
            llm_call=lambda prompt, key, model: "not json",
        )


def test_missing_api_key():
    with pytest.raises(RequirementAnalysisError, match="GEMINI_API_KEY"):
        analyze_requirements("text", api_key="")
