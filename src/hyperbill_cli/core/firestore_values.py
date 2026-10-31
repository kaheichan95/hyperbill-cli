"""Conversion between Python values and Firestore REST ``Value`` objects."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def encode(value: Any) -> dict[str, Any]:
    if value is None:
        return {"nullValue": None}
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, datetime):
        aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return {"timestampValue": aware.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")}
    if isinstance(value, str):
        return {"stringValue": value}
    if isinstance(value, (list, tuple)):
        return {"arrayValue": {"values": [encode(v) for v in value]}}
    if isinstance(value, dict):
        return {"mapValue": {"fields": encode_fields(value)}}
    raise TypeError(f"Cannot encode {type(value).__name__} for Firestore")


def encode_fields(data: dict[str, Any]) -> dict[str, Any]:
    return {key: encode(val) for key, val in data.items()}


def decode(value: dict[str, Any]) -> Any:
    if "nullValue" in value:
        return None
    if "booleanValue" in value:
        return value["booleanValue"]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "timestampValue" in value:
        return value["timestampValue"]
    if "stringValue" in value:
        return value["stringValue"]
    if "referenceValue" in value:
        return value["referenceValue"]
    if "geoPointValue" in value:
        return value["geoPointValue"]
    if "bytesValue" in value:
        return value["bytesValue"]
    if "arrayValue" in value:
        return [decode(v) for v in value["arrayValue"].get("values", [])]
    if "mapValue" in value:
        return decode_fields(value["mapValue"].get("fields", {}))
    return None


def decode_fields(fields: dict[str, Any]) -> dict[str, Any]:
    return {key: decode(val) for key, val in fields.items()}
