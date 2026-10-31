"""Sign-in flows. Each produces a dedicated Firebase session for this machine."""

from __future__ import annotations

from typing import Any

from ..core import credentials, identity, loopback
from ..core.context import AppContext


def _store(app: AppContext, tokens: identity.TokenSet, method: str) -> dict[str, Any]:
    credentials.save(
        app.env.name,
        credentials.StoredCredentials(refresh_token=tokens.refresh_token, uid=tokens.uid,
                                      email=tokens.email, method=method),
    )
    # Ensures the Hyperbill profile exists for first-time (e.g. Google) users.
    app.api.json("GET", "/api/user/profile")
    return {"signedIn": True, "env": app.env.name, "uid": tokens.uid, "email": tokens.email, "method": method}


def login_with_browser(app: AppContext, open_browser: bool) -> dict[str, Any]:
    refresh_token = loopback.browser_login(app.env, open_browser=open_browser)
    tokens = identity.refresh(app.env.firebase_api_key, refresh_token)
    return _store(app, tokens, "browser")


def login_with_password(app: AppContext, email: str, password: str) -> dict[str, Any]:
    tokens = identity.sign_in_with_password(app.env.firebase_api_key, email, password)
    return _store(app, tokens, "password")


def logout(app: AppContext) -> dict[str, Any]:
    return {"signedOut": credentials.delete(app.env.name), "env": app.env.name}


def whoami(app: AppContext) -> dict[str, Any]:
    profile = app.api.json("GET", "/api/user/profile").get("user", {})
    return {
        "env": app.env.name,
        "uid": app.session.uid,
        "email": profile.get("email") or app.session.email,
        "profile": profile.get("profile", {}),
        "language": profile.get("language"),
    }
