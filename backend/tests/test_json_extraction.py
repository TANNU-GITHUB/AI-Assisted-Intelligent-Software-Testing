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
