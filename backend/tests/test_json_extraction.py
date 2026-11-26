import pytest

from requirement_analysis.analyzer import _extract_json as extract_requirement_json
from test_generation.black_box import _extract_json as extract_black_box_json
from test_generation.white_box import _extract_json as extract_white_box_json


@pytest.mark.parametrize(
    "extract_json",
    [extract_requirement_json, extract_white_box_json, extract_black_box_json],
    ids=["requirements", "white-box", "black-box"],
)
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            '```json\n{"outer":{"items":[{"value":1}]}}\n```',
            {"outer": {"items": [{"value": 1}]}},
        ),
        (
            'Model response: [{"text":"brace } inside string","nested":[{"ok":true}]}] done',
            [{"text": "brace } inside string", "nested": [{"ok": True}]}],
        ),
    ],
)
def test_extract_json_preserves_nested_values(extract_json, text, expected):
    assert extract_json(text) == expected


@pytest.mark.parametrize(
    "extract_json",
    [extract_requirement_json, extract_white_box_json, extract_black_box_json],
    ids=["requirements", "white-box", "black-box"],
)
def test_extract_json_ignores_think_blocks_and_prose_arrays(extract_json):
    text = (
        "<think>Check range [0, 100] and threshold [25.0] first.</think>\n"
        "Here are ranges [1, 2]:\n"
        '{"requirements": [{"requirement_id": "REQ-01", "condition": "x < 0", "expected_result": "ValueError"}]}'
    )
    parsed = extract_json(text)
    assert isinstance(parsed, dict)
    assert parsed["requirements"][0]["requirement_id"] == "REQ-01"
