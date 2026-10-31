"""Structured errors so agents can branch on ``code`` instead of parsing prose."""

from __future__ import annotations

from typing import Any

EXIT_GENERAL = 1
EXIT_USAGE = 2
EXIT_AUTH = 3
EXIT_NOT_FOUND = 4
EXIT_CONFLICT = 5


class HyperbillError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "error",
        status: int | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.details = details

    @property
    def exit_code(self) -> int:
        if self.code in {"not_authenticated", "session_expired"} or self.status in {401}:
            return EXIT_AUTH
        if self.status == 404 or self.code == "not_found":
            return EXIT_NOT_FOUND
        if self.status == 409 or self.code in {"insufficient_funds", "conflict"}:
            return EXIT_CONFLICT
        if self.code == "invalid_input" or self.status == 400:
            return EXIT_USAGE
        return EXIT_GENERAL

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.status is not None:
            body["status"] = self.status
        if self.details is not None:
            body["details"] = self.details
        return body


def invalid_input(message: str) -> HyperbillError:
    return HyperbillError(message, code="invalid_input")


def not_found(message: str) -> HyperbillError:
    return HyperbillError(message, code="not_found")
