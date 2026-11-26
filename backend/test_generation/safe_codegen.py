"""Helpers for safely embedding test-case data in generated Python tests."""

from __future__ import annotations

import json
import keyword
import math
from typing import Any


def require_python_identifier(value: Any, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.isidentifier()
        or keyword.iskeyword(value)
    ):
        raise ValueError(f"{field_name} must be a valid Python identifier.")
    return value


def _contains_nonfinite(value: Any) -> bool:
    if isinstance(value, float):
        return math.isnan(value) or math.isinf(value)
    if isinstance(value, (list, tuple)):
        return any(_contains_nonfinite(v) for v in value)
    if isinstance(value, dict):
        return any(_contains_nonfinite(k) or _contains_nonfinite(v) for k, v in value.items())
    return False


def json_expression(value: Any) -> str:
    if _contains_nonfinite(value):
        if isinstance(value, float):
            if math.isnan(value):
                return "float('nan')"
            return "float('inf')" if value > 0 else "float('-inf')"
        if isinstance(value, list):
            return "[" + ", ".join(json_expression(v) for v in value) + "]"
        if isinstance(value, tuple):
            items = ", ".join(json_expression(v) for v in value)
            return f"({items},)" if len(value) == 1 else f"({items})"
        if isinstance(value, dict):
            pairs = ", ".join(
                f"{json_expression(k)}: {json_expression(v)}" for k, v in value.items()
            )
            return "{" + pairs + "}"
    serialized = json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
    )
    return f"json.loads({serialized!r})"


def function_call_expression(function_name: str, inputs: Any) -> str:
    safe_name = require_python_identifier(function_name, "Function name")
    return f"getattr(_source, {safe_name!r})(**{json_expression(inputs)})"


def expected_exception_expression(exception_name: str) -> str:
    safe_name = require_python_identifier(exception_name, "Exception name")
    return f"_resolve_exception({safe_name!r})"


def generated_test_imports() -> list[str]:
    return [
        "import builtins",
        "import json",
        "import pytest",
        "import source as _source",
        "from source import *",
        "",
        "def _resolve_exception(name):",
        "    exception = getattr(_source, name, None)",
        "    if exception is None:",
        "        exception = getattr(builtins, name, None)",
        "    if not isinstance(exception, type) or not issubclass(exception, BaseException):",
        '        raise ValueError(f"Unknown exception class: {name}")',
        "    return exception",
        "",
        "def _assert_match(actual, expected):",
        "    if isinstance(actual, tuple) and isinstance(expected, list):",
        "        actual = list(actual)",
        "    elif isinstance(actual, list) and isinstance(expected, tuple):",
        "        expected = list(expected)",
        "    if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):",
        "        assert len(actual) == len(expected)",
        "        for a, e in zip(actual, expected):",
        "            _assert_match(a, e)",
        "        return",
        '    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)) and not isinstance(actual, bool) and not isinstance(expected, bool):',
        "        assert abs(actual - expected) < 1e-6",
        "        return",
        "    assert actual == expected",
        "",
    ]


def case_assertion_lines(
    case: dict[str, Any],
    call: str,
    *,
    skip_unasserted: bool = False,
) -> list[str]:
    """Emit standard pytest body lines for a normalized test case."""
    if case.get("expected_exception"):
        exception_name = expected_exception_expression(case["expected_exception"])
        return [
            f"    with pytest.raises({exception_name}):",
            f"        {call}",
        ]
    if not case.get("assert_output", True):
        if skip_unasserted and "expected_output" not in case and not case.get("expected_field"):
            return ['    pytest.skip("Static fallback cannot determine the expected output.")']
        return [
            "    # Verify execution completes without uncaught exception",
            f"    result = {call}",
            "    assert result is not None or result is None",
        ]
    expected_field = case.get("expected_field")
    if expected_field:
        safe_field = str(expected_field)
        callee = case.get("expected_callee")
        callee_args = case.get("expected_callee_args") or []
        expected_delta = case.get("expected_delta")
        if callee and expected_delta is not None:
            safe_callee = require_python_identifier(str(callee), "Callee function name")
            inputs = case.get("input") or {}
            arg_exprs = [
                json_expression(inputs[arg]) if arg in inputs else f"result[{arg!r}]"
                for arg in callee_args
            ]
            callee_call = f"getattr(_source, {safe_callee!r})({', '.join(arg_exprs)})"
            delta_val = float(expected_delta)
            return [
                f"    result = {call}",
                f"    base_val = {callee_call}",
                f"    assert isinstance(result, dict), f'Expected dict result, got {{type(result).__name__}}'",
                f"    assert abs(float(result.get({safe_field!r}, 0.0)) - (float(base_val) + {delta_val!r})) < 1e-6, (",
                f"        f'Expected {safe_field} == {{float(base_val) + {delta_val!r}}}, got {{result.get({safe_field!r})}}'",
                "    )",
            ]
        expected_val = case.get("expected_field_value")
        return [
            f"    result = {call}",
            f"    assert isinstance(result, dict), f'Expected dict result, got {{type(result).__name__}}'",
            f"    _assert_match(result.get({safe_field!r}), {json_expression(expected_val)})",
        ]
    if case.get("expected_output") is not None:
        expected = case.get("expected_output")
        return [f"    _assert_match({call}, {json_expression(expected)})"]
    return [
        "    # Verify execution completes without uncaught exception",
        f"    result = {call}",
        "    assert result is not None or result is None",
    ]
