"""Load and validate bidding-logic ASTs before they are sent to the server.

The auctioneer fails closed on malformed ASTs (the campaign silently never
wins), so catching mistakes client-side saves agents a lot of confusion.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..core.errors import invalid_input
from .condition_schema import FIELDS

_TIME = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d$")


def load_bidding_logic(source: str | None) -> dict[str, Any] | None:
    """Accept inline JSON, ``@path/to/file.json`` or ``none``. Returns ``{"condition": ...}``."""
    if source is None:
        return None
    if source.strip().lower() == "none":
        return {"condition": None}

    text = Path(source[1:]).read_text() if source.startswith("@") else source
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise invalid_input(f"Condition is not valid JSON: {exc}") from exc

    if isinstance(parsed, dict) and "condition" in parsed and parsed.get("type") is None:
        condition = parsed["condition"]
    else:
        condition = parsed
    if condition is not None:
        validate(condition)
    return {"condition": condition}


def validate(node: Any, path: str = "condition", scope: str = "context") -> None:
    if not isinstance(node, dict):
        raise invalid_input(f"{path}: expected an object")
    kind = node.get("type")
    if kind == "logical":
        _validate_logical(node, path, scope)
    elif kind == "condition":
        _validate_condition(node, path, scope)
    else:
        raise invalid_input(f"{path}: type must be 'condition' or 'logical'")


def _validate_logical(node: dict, path: str, scope: str) -> None:
    operator = node.get("operator")
    children = node.get("children")
    if operator not in {"and", "or", "not"}:
        raise invalid_input(f"{path}: logical operator must be and/or/not")
    if not isinstance(children, list) or not children:
        raise invalid_input(f"{path}: children must be a non-empty list")
    if operator == "not" and len(children) != 1:
        raise invalid_input(f"{path}: 'not' takes exactly one child")
    for index, child in enumerate(children):
        validate(child, f"{path}.children[{index}]", scope)


def _validate_condition(node: dict, path: str, scope: str) -> None:
    field = node.get("field")
    operator = node.get("operator")
    value = node.get("value")

    definition = FIELDS.get(field)
    if definition is None:
        raise invalid_input(f"{path}: unknown field '{field}'. Run `hyperbill conditions schema`.")
    if not field.startswith(f"{scope}."):
        raise invalid_input(f"{path}: field '{field}' is not valid here (expected {scope}.* fields)")
    if operator not in definition["operators"]:
        raise invalid_input(f"{path}: operator '{operator}' not allowed on {field}; use one of {definition['operators']}")

    if definition["type"] == "array" and definition.get("element") == "person":
        validate(value, f"{path}.value", scope="person")
        return
    _validate_value(definition, field, operator, value, path)


def _validate_value(definition: dict, field: str, operator: str, value: Any, path: str) -> None:
    kind = definition["type"]
    allowed = definition.get("values")
    expects_list = operator in {"in", "not-in", "array-contains-any", "array-contains-all"}

    items = value if isinstance(value, list) else [value]
    if expects_list and not isinstance(value, list):
        raise invalid_input(f"{path}: operator '{operator}' requires a list value")

    for item in items:
        if kind == "time" and not (isinstance(item, str) and _TIME.match(item)):
            raise invalid_input(f"{path}: {field} expects HH:MM, got {item!r}")
        if kind == "number" and (isinstance(item, bool) or not isinstance(item, (int, float))):
            raise invalid_input(f"{path}: {field} expects a number, got {item!r}")
        if allowed is not None and item not in allowed:
            raise invalid_input(f"{path}: {item!r} is not a valid value for {field}")
