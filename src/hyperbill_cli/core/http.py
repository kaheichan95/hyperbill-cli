"""Authenticated client for the public Hyperbill web API (``/api/*``)."""

from __future__ import annotations

from typing import Any

import requests

from .errors import HyperbillError
from .session import Session

TIMEOUT_SECONDS = 60


class ApiClient:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.base_url = session.env.base_url

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        authenticated: bool = True,
        timeout: float = TIMEOUT_SECONDS,
    ) -> requests.Response:
        response = self._send(method, path, json, params, authenticated, timeout, force_refresh=False)
        if response.status_code == 401 and authenticated:
            response = self._send(method, path, json, params, authenticated, timeout, force_refresh=True)
        if not response.ok:
            raise _to_error(response)
        return response

    def json(self, method: str, path: str, **kwargs: Any) -> Any:
        return self.request(method, path, **kwargs).json()

    def _send(
        self,
        method: str,
        path: str,
        json: Any,
        params: dict[str, Any] | None,
        authenticated: bool,
        timeout: float,
        force_refresh: bool,
    ) -> requests.Response:
        headers = {"Accept": "application/json"}
        if authenticated:
            headers["Authorization"] = f"Bearer {self.session.id_token(force_refresh=force_refresh)}"
        try:
            return requests.request(
                method,
                f"{self.base_url}{path}",
                json=json,
                params=params,
                headers=headers,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise HyperbillError(f"Could not reach {self.base_url}: {exc}", code="network_error") from exc


def _to_error(response: requests.Response) -> HyperbillError:
    try:
        body = response.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    message = body.get("error") or body.get("detail")
    code = body.get("code")
    details = message if isinstance(message, (list, dict)) else None
    if details is not None:
        return HyperbillError("Request rejected", code=code or _default_code(response.status_code),
                              status=response.status_code, details=details)
    if not isinstance(message, str):
        message = f"HTTP {response.status_code} from {response.url.split('?')[0]}"
    return HyperbillError(message, code=code or _default_code(response.status_code), status=response.status_code)


def _default_code(status: int) -> str:
    return {
        400: "invalid_input",
        401: "not_authenticated",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
    }.get(status, "api_error")
