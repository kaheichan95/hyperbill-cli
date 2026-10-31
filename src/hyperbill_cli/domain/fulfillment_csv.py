"""CSV export matching the web's ``lib/utils/fulfillment-csv.ts`` column layout."""

from __future__ import annotations

import json
from typing import Any

PRIORITY_HEADERS = [
    "id", "timestamp", "time", "bidPrice", "fulfillmentPrice", "totalPrice",
    "mediaFileId", "context.deviceId", "context.time", "context.weekday",
]


def _strip_geometry(value: Any) -> Any:
    if isinstance(value, list):
        return [_strip_geometry(v) for v in value]
    if isinstance(value, dict):
        return {k: _strip_geometry(v) for k, v in value.items() if k not in {"bbox", "features"}}
    return value


def _animal_labels(raw: list) -> list:
    if raw and isinstance(raw[0], dict) and "label" in raw[0]:
        return [entry["label"] for entry in raw if isinstance(entry, dict) and "label" in entry]
    return raw


def _flatten_context(ctx: dict[str, Any]) -> dict[str, Any]:
    persons: list = []
    animals: list = []
    time_val = ctx.get("time")
    weekday_val = ctx.get("weekday")
    for frame in ctx.get("features") or []:
        if not isinstance(frame, dict):
            continue
        time_val = time_val or frame.get("time")
        weekday_val = weekday_val or frame.get("weekday")
        persons.extend(frame.get("persons") or [])
        animals.extend(frame.get("animals") or [])

    flattened = {k: v for k, v in ctx.items() if k != "features"}
    if ctx.get("features") and time_val and weekday_val:
        flattened.update(time=time_val, weekday=weekday_val, persons=persons, animals=_animal_labels(animals))
    return _strip_geometry(flattened)


def _flatten(value: Any, prefix: str, out: dict[str, str]) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            _flatten(nested, f"{prefix}.{key}" if prefix else key, out)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _flatten(item, f"{prefix}.{index}" if prefix else str(index), out)
    elif prefix:
        out[prefix] = "" if value is None else (json.dumps(value) if isinstance(value, (dict, list)) else str(value))


def _sort_key(header: str) -> tuple[int, str]:
    return (PRIORITY_HEADERS.index(header), "") if header in PRIORITY_HEADERS else (len(PRIORITY_HEADERS), header)


def _cell(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def to_csv(fulfillments: list[dict[str, Any]]) -> str:
    rows = []
    for record in fulfillments:
        normalized = dict(record)
        if isinstance(record.get("context"), dict):
            normalized["context"] = _flatten_context(record["context"])
        flat: dict[str, str] = {}
        _flatten(normalized, "", flat)
        rows.append(flat)

    headers = sorted({key for row in rows for key in row}, key=_sort_key)
    lines = [",".join(_cell(h) for h in headers)]
    lines += [",".join(_cell(row.get(h, "")) for h in headers) for row in rows]
    return "\n".join(lines)
