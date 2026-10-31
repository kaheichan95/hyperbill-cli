"""Firebase Authentication REST calls (the same endpoints the web SDK uses)."""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass

import requests

from .errors import HyperbillError

IDENTITY_URL = "https://identitytoolkit.googleapis.com/v1"
SECURE_TOKEN_URL = "https://securetoken.googleapis.com/v1/token"
TIMEOUT_SECONDS = 20

_SESSION_ENDED = {
    "TOKEN_EXPIRED",
    "USER_DISABLED",
    "USER_NOT_FOUND",
    "INVALID_REFRESH_TOKEN",
    "INVALID_GRANT_TYPE",
}


@dataclass
class TokenSet:
    id_token: str
    refresh_token: str
    expires_at: float
    uid: str
    email: str | None


def sign_in_with_password(api_key: str, email: str, password: str) -> TokenSet:
    response = requests.post(
        f"{IDENTITY_URL}/accounts:signInWithPassword",
        params={"key": api_key},
        json={"email": email, "password": password, "returnSecureToken": True},
        timeout=TIMEOUT_SECONDS,
    )
    body = _json_or_raise(response, failure_code="login_failed")
    return TokenSet(
        id_token=body["idToken"],
        refresh_token=body["refreshToken"],
        expires_at=time.time() + int(body.get("expiresIn", 3600)),
        uid=body["localId"],
        email=body.get("email"),
    )


def refresh(api_key: str, refresh_token: str) -> TokenSet:
    response = requests.post(
        SECURE_TOKEN_URL,
        params={"key": api_key},
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        timeout=TIMEOUT_SECONDS,
    )
    body = _json_or_raise(response, failure_code="session_expired")
    id_token = body["id_token"]
    return TokenSet(
        id_token=id_token,
        refresh_token=body.get("refresh_token", refresh_token),
        expires_at=time.time() + int(body.get("expires_in", 3600)),
        uid=body["user_id"],
        email=_unverified_claims(id_token).get("email"),
    )


def _json_or_raise(response: requests.Response, failure_code: str) -> dict:
    try:
        body = response.json()
    except ValueError:
        body = {}
    if response.ok:
        return body

    reason = (body.get("error") or {}).get("message", f"HTTP {response.status_code}")
    reason_key = reason.split(" ")[0].split(":")[0]
    if failure_code == "session_expired" and reason_key in _SESSION_ENDED:
        raise HyperbillError(
            "Your CLI session has ended (revoked, expired or password changed). Run `hyperbill auth login`.",
            code="session_expired",
            status=401,
        )
    raise HyperbillError(f"Firebase authentication failed: {reason}", code=failure_code, status=response.status_code)


def _unverified_claims(id_token: str) -> dict:
    """Read display-only claims (email). Never used for authorization decisions."""
    try:
        payload = id_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError):
        return {}
