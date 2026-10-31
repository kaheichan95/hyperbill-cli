"""Environment selection: which Hyperbill site and Firebase project to talk to.

Firebase web API keys and project IDs are public client identifiers (they ship
in every browser bundle); authorization comes solely from the user's ID token.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urlparse

from .errors import invalid_input


@dataclass(frozen=True)
class Environment:
    name: str
    base_url: str
    firebase_api_key: str
    project_id: str
    storage_bucket: str

    @property
    def origin(self) -> str:
        parsed = urlparse(self.base_url)
        return f"{parsed.scheme}://{parsed.netloc}"


ENVIRONMENTS: dict[str, Environment] = {
    "prod": Environment(
        name="prod",
        base_url="https://hyperbill.co",
        firebase_api_key="AIzaSyBuDUEVeZKzORADDNS-8XD0jktyFB-B5_4",
        project_id="hyperbill-prod-e7495",
        storage_bucket="hyperbill-prod-e7495.firebasestorage.app",
    ),
    "dev": Environment(
        name="dev",
        base_url="http://localhost:3000",
        firebase_api_key="AIzaSyCzVvqeysKttdOBcUGqA8i4lnxOx4cMun8",
        project_id="hyperbill-dev",
        storage_bucket="hyperbill-dev.firebasestorage.app",
    ),
}

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def resolve_environment(name: str | None) -> Environment:
    env_name = name or os.environ.get("HYPERBILL_ENV", "prod")
    if env_name not in ENVIRONMENTS:
        raise invalid_input(f"Unknown environment '{env_name}'. Choose one of: {', '.join(ENVIRONMENTS)}")
    env = ENVIRONMENTS[env_name]

    base_url = os.environ.get("HYPERBILL_BASE_URL")
    if base_url:
        env = replace(env, base_url=base_url.rstrip("/"))
    _require_secure_transport(env.base_url)
    return env


def _require_secure_transport(base_url: str) -> None:
    """ID tokens are bearer credentials: never send them over plain HTTP off-box."""
    parsed = urlparse(base_url)
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and parsed.hostname in _LOCAL_HOSTS:
        return
    raise invalid_input(f"Refusing insecure base URL {base_url}: HTTPS is required for non-local hosts")


def config_dir() -> Path:
    override = os.environ.get("HYPERBILL_CONFIG_DIR")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return (Path(xdg) if xdg else Path.home() / ".config") / "hyperbill"
