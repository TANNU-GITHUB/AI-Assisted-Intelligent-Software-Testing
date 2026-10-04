"""
Data transformation utilities (Case 04 — functional code only; NFRs live in requirements.txt).
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable

SCHEMA_VERSION = "1.4.0"
MAX_COLUMNS = 512
NULL_TOKENS = frozenset({"", "na", "null", "none", "n/a"})


def normalize_column_name(name: str) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", name.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "column"


def normalize_headers(headers: list[str]) -> list[str]:
    normalized = [normalize_column_name(h) for h in headers]
    if len(normalized) != len(set(normalized)):
        raise ValueError("duplicate columns after normalization")
    if len(normalized) > MAX_COLUMNS:
        raise ValueError("too many columns")
    return normalized


def parse_cell(value: str) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in NULL_TOKENS:
        return None
    try:
        if "." in text or "e" in text.lower():
            return float(text)
        return int(text)
    except ValueError:
        return text


def parse_row(headers: list[str], cells: list[str]) -> dict[str, Any]:
    if len(cells) != len(headers):
        raise ValueError("row width mismatch")
    return {headers[i]: parse_cell(cells[i]) for i in range(len(headers))}


def parse_csv_text(csv_text: str) -> list[dict[str, Any]]:
    lines = [line for line in csv_text.splitlines() if line.strip()]
    if not lines:
        return []
    headers = normalize_headers(lines[0].split(","))
    rows: list[dict[str, Any]] = []
    for line in lines[1:]:
        rows.append(parse_row(headers, line.split(",")))
    return rows


def numeric_mean(values: Iterable[Any]) -> float | None:
    nums = [float(v) for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return sum(nums) / len(nums)


def numeric_sum(values: Iterable[Any]) -> float:
    return float(sum(float(v) for v in values if isinstance(v, (int, float))))


def filter_rows(rows: list[dict[str, Any]], key: str, equals: Any) -> list[dict[str, Any]]:
    return [row for row in rows if row.get(key) == equals]


def project_columns(rows: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    return [{key: row.get(key) for key in keys} for row in rows]


def group_by(rows: list[dict[str, Any]], key: str) -> dict[Any, list[dict[str, Any]]]:
    groups: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        bucket = row.get(key)
        groups.setdefault(bucket, []).append(row)
    return groups


def aggregate_group_means(rows: list[dict[str, Any]], group_key: str, value_key: str) -> dict[Any, float]:
    grouped = group_by(rows, group_key)
    result: dict[Any, float] = {}
    for key, bucket in grouped.items():
        mean = numeric_mean(row.get(value_key) for row in bucket)
        if mean is not None:
            result[key] = mean
    return result


def to_json_export(rows: list[dict[str, Any]]) -> str:
    payload = {"schema_version": SCHEMA_VERSION, "rows": rows}
    return json.dumps(payload, ensure_ascii=False)


def from_json_export(text: str) -> list[dict[str, Any]]:
    data = json.loads(text)
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("schema mismatch")
    return list(data.get("rows") or [])


def slugify(value: str) -> str:
    return normalize_column_name(value)


def coerce_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def coerce_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def trim_strings(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in row.items():
        if isinstance(val, str):
            out[key] = val.strip()
        else:
            out[key] = val
    return out


def drop_none_rows(rows: list[dict[str, Any]], required_key: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get(required_key) is not None]


def rename_key(row: dict[str, Any], old: str, new: str) -> dict[str, Any]:
    if old not in row:
        return dict(row)
    updated = dict(row)
    updated[new] = updated.pop(old)
    return updated


def merge_rows(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = dict(left)
    merged.update(right)
    return merged


def distinct_values(rows: list[dict[str, Any]], key: str) -> list[Any]:
    seen: set[Any] = set()
    out: list[Any] = []
    for row in rows:
        val = row.get(key)
        if val not in seen:
            seen.add(val)
            out.append(val)
    return out


def sort_rows(rows: list[dict[str, Any]], key: str, reverse: bool = False) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: row.get(key), reverse=reverse)


def clamp_number(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def percent_change(old: float, new: float) -> float | None:
    if old == 0:
        return None
    return (new - old) / old * 100.0


def moving_average(series: list[float], window: int) -> list[float | None]:
    if window <= 0:
        raise ValueError("window")
    out: list[float | None] = []
    for index in range(len(series)):
        if index + 1 < window:
            out.append(None)
            continue
        chunk = series[index + 1 - window : index + 1]
        out.append(sum(chunk) / window)
    return out


def z_score(value: float, mean: float, stdev: float) -> float | None:
    if stdev == 0:
        return None
    return (value - mean) / stdev


def standard_deviation(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return var ** 0.5


def bucketize(value: float, edges: list[float]) -> int:
    for index, edge in enumerate(edges):
        if value < edge:
            return index
    return len(edges)


def pivot_counts(rows: list[dict[str, Any]], key: str) -> dict[Any, int]:
    counts: dict[Any, int] = {}
    for row in rows:
        val = row.get(key)
        counts[val] = counts.get(val, 0) + 1
    return counts


def validate_row_width(row: dict[str, Any], max_cols: int = MAX_COLUMNS) -> None:
    if len(row) > max_cols:
        raise ValueError("row too wide")


def hash_row(row: dict[str, Any]) -> str:
    return json.dumps(row, sort_keys=True, default=str)


def dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        digest = hash_row(row)
        if digest in seen:
            continue
        seen.add(digest)
        out.append(row)
    return out


def split_train_test(rows: list[dict[str, Any]], ratio: float = 0.8) -> tuple[list[dict], list[dict]]:
    if not 0 < ratio < 1:
        raise ValueError("ratio")
    cut = int(len(rows) * ratio)
    return rows[:cut], rows[cut:]


def impute_mean(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    mean = numeric_mean(row.get(key) for row in rows)
    if mean is None:
        return list(rows)
    filled: list[dict[str, Any]] = []
    for row in rows:
        updated = dict(row)
        if updated.get(key) is None:
            updated[key] = mean
        filled.append(updated)
    return filled
