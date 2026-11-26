"""Helpers for extracting JSON values from model responses."""

from __future__ import annotations

import json
import re
from typing import Any


_FENCED_JSON = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)


def _is_structured_payload(value: Any) -> bool:
    if isinstance(value, dict) and bool(value):
        return True
    if isinstance(value, list) and any(isinstance(item, dict) for item in value):
        return True
    return False


def extract_json(text: str) -> Any:
    raw = text.strip()
    stripped = _THINK_BLOCK.sub("", raw).strip()

    candidates: list[str] = []
    for source in (stripped, raw):
        if not source:
            continue
        for match in _FENCED_JSON.finditer(source):
            block = match.group(1).strip()
            if block and block not in candidates:
                candidates.append(block)
    if stripped and stripped not in candidates:
        candidates.append(stripped)
    if raw and raw not in candidates:
        candidates.append(raw)

    decoder = json.JSONDecoder()
    first_decoded: tuple[bool, Any] | None = None

    for candidate in candidates:
        pos = 0
        length = len(candidate)
        while pos < length:
            character = candidate[pos]
            if character not in "{[":
                pos += 1
                continue
            try:
                value, end = decoder.raw_decode(candidate, pos)
            except json.JSONDecodeError:
                pos += 1
                continue
            if _is_structured_payload(value):
                return value
            if first_decoded is None:
                first_decoded = (True, value)
            pos = end

    if first_decoded is not None:
        return first_decoded[1]

    raise json.JSONDecodeError("No JSON object or array found", raw, 0)
