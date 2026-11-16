"""Helpers for extracting JSON values from model responses."""

from __future__ import annotations

import json
import re
from typing import Any


_FENCED_JSON = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)


def extract_json(text: str) -> Any:
    cleaned = text.strip()
    candidates = [match.group(1).strip() for match in _FENCED_JSON.finditer(cleaned)]
    candidates.append(cleaned)
    decoder = json.JSONDecoder()

    for candidate in candidates:
        for index, character in enumerate(candidate):
            if character not in "{[":
                continue
            try:
                value, _ = decoder.raw_decode(candidate, index)
            except json.JSONDecodeError:
                continue
            return value

    raise json.JSONDecodeError("No JSON object or array found", cleaned, 0)
