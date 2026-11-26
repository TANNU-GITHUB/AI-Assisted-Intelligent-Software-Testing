import json

from requirement_analysis.analyzer import analyze_requirements


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


def test_falls_back_after_invalid_json():
    result = analyze_requirements(
        "Members receive a 10% discount. Negative prices must be rejected.",
        api_key="test-key",
        llm_call=lambda prompt, key, model: "not json",
    )
    assert result["requirement_count"] >= 1
    assert result["model"] == "heuristic-fallback"


def test_missing_api_key_uses_heuristic_when_llm_fails():
    result = analyze_requirements(
        "Members receive a 10% discount.",
        api_key="",
        llm_call=lambda prompt, key, model: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    assert result["requirement_count"] >= 1
    assert result["model"] == "heuristic-fallback"


def test_requirements_with_curly_braces_do_not_crash():
    captured = {}

    def capture(prompt, key, model):
        captured["prompt"] = prompt
        raise RuntimeError("forced")

    result = analyze_requirements(
        "Return a dict like {total: 0} when the cart is empty.",
        api_key="test-key",
        llm_call=capture,
    )
    assert "{total: 0}" in captured["prompt"]
    assert result["requirement_count"] >= 1
    assert result["model"] == "heuristic-fallback"


def test_llm_error_does_not_retry_with_strict_prompt():
    from llm_client import LLMError

    calls = {"n": 0}

    def failing_llm(prompt, key, model):
        calls["n"] += 1
        raise LLMError("provider timed out")

    result = analyze_requirements(
        "Scores below 0 raise ValueError.\nScores that are NAN must raise value error.",
        api_key="test-key",
        llm_call=failing_llm,
    )
    assert calls["n"] == 1
    assert result["model"] == "heuristic-fallback"
    assert result["requirement_count"] == 2


def test_reflows_word_per_line_pdf_text_and_ignores_headers_without_duplicates():
    messy_pdf_text = (
        "\ufeffRequirements:-\n\n"
        "●\n\nReject\n\nnegative\n\nprices\n\nwith\n\nValueError.\n\n"
        "●\n\nMembers\n\nget\n\n10%\n\noff.\n\n"
        "●\n\nNon-\nmembers\n\npay\n\na\n\n$5\n\ndelivery\n\nfee."
    )
    result = analyze_requirements(
        messy_pdf_text,
        api_key="",
        llm_call=lambda *_args: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    assert result["requirement_count"] == 3
    conditions = [r["condition"] for r in result["requirements"]]
    assert conditions == [
        "Reject negative prices with ValueError.",
        "Members get 10% off.",
        "Non-members pay a $5 delivery fee.",
    ]

    # When LLM omits 2 of 3 bulleted items and input starts with 'Requirements:-', do not add 'Requirements:-' or duplicate covered items.
    partial_llm = json.dumps(
        {
            "requirements": [
                {
                    "requirement_id": "REQ-01",
                    "condition": "price < 0",
                    "expected_result": "raise ValueError",
                    "source_excerpt": "Reject negative prices with ValueError.",
                }
            ]
        }
    )
    bulleted = (
        "Requirements:-\n\n"
        "* Reject negative prices with ValueError.\n"
        "* Members get 10% off.\n"
        "* Non-members pay a $5 delivery fee.\n"
    )
    merged = analyze_requirements(
        bulleted,
        api_key="k",
        llm_call=lambda *_args: partial_llm,
    )
    assert merged["requirement_count"] == 3
    assert all("Requirements" not in r["condition"] for r in merged["requirements"])


def test_splits_inline_numbered_list_with_zero_width_space_even_when_llm_returns_one():
    inline_zwsp = (
        "1.\u200bReject negative prices with ValueError. "
        "2.\u200bMembers get 10% off. "
        "3.\u200bNon-members pay a $5 delivery fee."
    )
    partial_llm = json.dumps(
        {
            "requirements": [
                {
                    "requirement_id": "REQ-01",
                    "condition": "Price is negative (< 0)",
                    "expected_result": "System raises ValueError",
                    "source_excerpt": "Reject negative prices with ValueError.",
                }
            ]
        }
    )
    result = analyze_requirements(
        inline_zwsp,
        api_key="k",
        llm_call=lambda *_args: partial_llm,
    )
    assert result["requirement_count"] == 3


def test_lowercase_function_lines_are_not_merged_into_req01():
    text = (
        "calculate_electricity_bill must raise ValueError when units < 0.\n"
        "calculate_electricity_bill returns 550.0 when units == 100 and is_commercial is False.\n"
        "calculate_water_bill must raise ValueError when liters < 0.\n"
        "calculate_water_bill must raise ValueError when liters > 10000.\n"
    )
    result = analyze_requirements(
        text,
        api_key="",
        llm_call=lambda *_args: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    assert result["requirement_count"] == 4
    assert [r["requirement_id"] for r in result["requirements"]] == [
        "REQ-01",
        "REQ-02",
        "REQ-03",
        "REQ-04",
    ]
