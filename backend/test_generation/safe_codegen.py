"""Helpers for safely embedding test-case data in generated Python tests."""

from __future__ import annotations

import json
import keyword
from typing import Any


def require_python_identifier(value: Any, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.isidentifier()
        or keyword.iskeyword(value)
    ):
        raise ValueError(f"{field_name} must be a valid Python identifier.")
    return value


def json_expression(value: Any) -> str:
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
    ]
