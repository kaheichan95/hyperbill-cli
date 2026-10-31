"""Merchant category codes required when uploading media (same list as the web)."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

from ..core.errors import invalid_input


@lru_cache(maxsize=1)
def catalogue() -> list[dict[str, str]]:
    return json.loads(resources.files("hyperbill_cli").joinpath("data/mcc.json").read_text())


def search(text: str | None) -> list[dict[str, str]]:
    if not text:
        return catalogue()
    needle = text.lower()
    return [m for m in catalogue() if needle in m["name"].lower() or needle in m["code"]]


def require_code(code: str) -> str:
    if not any(m["code"] == code for m in catalogue()):
        raise invalid_input(f"Unknown merchant category code '{code}'. Run `hyperbill media mcc --search <term>`.")
    return code
