from pathlib import Path

from test_generation.black_box import _fallback_cases as black_box_fallback
from test_generation.black_box import _write_pytest_file as write_black_box
from test_generation.other_tests import (
    _fallback_integration_tests,
    _write_pytest_file as write_other_tests,
)
from test_generation.white_box import _fallback_cases as white_box_fallback
from test_generation.white_box import _write_pytest_file as write_white_box


def _source_with_side_effect(marker: Path, function_source: str) -> str:
    return f"open({str(marker)!r}, 'w').write('executed')\n\n{function_source}"


def test_white_box_fallback_analyzes_source_without_executing_it(tmp_path, monkeypatch):
    marker = tmp_path / "white-box-executed"
    source = _source_with_side_effect(marker, "def target(value: int):\n    return value\n")
    cases = white_box_fallback(
        {
            "name": "target",
            "qualified_name": "target",
            "params": [{"name": "value", "annotation": "int"}],
            "branches": [],
        },
        source,
    )
    cases[0]["requirement_id"] = "REQ-01"
    monkeypatch.setattr("test_generation.white_box.session_dir", lambda _session_id: tmp_path)
    test_file = Path(write_white_box("session", "target", cases))
    content = test_file.read_text(encoding="utf-8")

    assert not marker.exists()
    assert cases[0]["assert_output"] is False
    assert "result = getattr(_source, 'target')" in content
    assert "assert result is not None" in content


def test_black_box_fallback_analyzes_source_without_executing_it(tmp_path, monkeypatch):
    marker = tmp_path / "black-box-executed"
    source = _source_with_side_effect(marker, "def target(value: int):\n    return value\n")
    cases = black_box_fallback(
        [{"requirement_id": "REQ-01", "condition": "returns a value"}],
        [{"name": "target", "params": [{"name": "value", "annotation": "int"}]}],
        source,
    )
    monkeypatch.setattr("test_generation.black_box.session_dir", lambda _session_id: tmp_path)
    test_file = Path(write_black_box("session", cases))
    content = test_file.read_text(encoding="utf-8")

    assert not marker.exists()
    assert cases[0]["assert_output"] is False
    assert "result = getattr(_source, 'target')" in content
    assert "assert result is not None" in content


def test_integration_fallback_analyzes_source_without_executing_it(tmp_path, monkeypatch):
    marker = tmp_path / "integration-executed"
    source = _source_with_side_effect(
        marker,
        "def caller(value: int):\n    return callee(value)\n\n"
        "def callee(value: int):\n    return value\n",
    )
    cases = _fallback_integration_tests(
        source,
        [{"caller": "caller", "callee": "callee"}],
        ["REQ-01"],
    )
    monkeypatch.setattr("test_generation.other_tests.session_dir", lambda _session_id: tmp_path)
    test_file = Path(write_other_tests("session", "integration", cases))
    content = test_file.read_text(encoding="utf-8")

    assert not marker.exists()
    assert cases[0]["assert_output"] is False
    assert "result = getattr(_source, 'caller')" in content
    assert "assert result is not None" in content
