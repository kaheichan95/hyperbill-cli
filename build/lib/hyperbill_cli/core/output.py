"""Machine-readable output: JSON on stdout, JSON errors on stderr."""

from __future__ import annotations

import json
import sys
from typing import Any

from .errors import HyperbillError


def emit(data: Any) -> None:
    sys.stdout.write(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n")


def emit_error(error: HyperbillError) -> None:
    sys.stderr.write(json.dumps({"error": error.to_dict()}, indent=2, ensure_ascii=False, default=str) + "\n")
