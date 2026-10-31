"""Resolves the signed-in user and hands out fresh Firebase ID tokens.

Refresh token sources, in priority order:
1. ``HYPERBILL_REFRESH_TOKEN`` env var (for sandboxed / headless agents)
2. the credential store written by ``hyperbill auth login``
"""

from __future__ import annotations

import os
import time

from . import credentials, identity
from .config import Environment
from .errors import HyperbillError

REFRESH_MARGIN_SECONDS = 300
REFRESH_TOKEN_ENV = "HYPERBILL_REFRESH_TOKEN"


class Session:
    def __init__(self, env: Environment) -> None:
        self.env = env
        self._tokens: identity.TokenSet | None = None
        self._stored: credentials.StoredCredentials | None = None

    def _refresh_token(self) -> str:
        from_env = os.environ.get(REFRESH_TOKEN_ENV)
        if from_env:
            return from_env
        self._stored = credentials.load(self.env.name)
        if not self._stored:
            raise HyperbillError(
                "Not signed in. Run `hyperbill auth login` (or set HYPERBILL_REFRESH_TOKEN).",
                code="not_authenticated",
            )
        return self._stored.refresh_token

    def id_token(self, force_refresh: bool = False) -> str:
        if force_refresh or not self._tokens or self._tokens.expires_at - time.time() < REFRESH_MARGIN_SECONDS:
            self._tokens = identity.refresh(self.env.firebase_api_key, self._refresh_token())
            self._persist_rotation()
        return self._tokens.id_token

    def _persist_rotation(self) -> None:
        stored = self._stored
        if stored and self._tokens and self._tokens.refresh_token != stored.refresh_token:
            stored.refresh_token = self._tokens.refresh_token
            credentials.save(self.env.name, stored)

    @property
    def uid(self) -> str:
        self.id_token()
        assert self._tokens is not None
        return self._tokens.uid

    @property
    def email(self) -> str | None:
        self.id_token()
        assert self._tokens is not None
        return self._tokens.email
