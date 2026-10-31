"""On-disk credential store, readable only by the current OS user.

Only the long-lived refresh token is persisted; ID tokens live for an hour and
are re-minted on demand. Credentials are keyed by environment name.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import config_dir


@dataclass
class StoredCredentials:
    refresh_token: str
    uid: str
    email: str | None = None
    method: str | None = None


def credentials_path() -> Path:
    return config_dir() / "credentials.json"


def _read_all() -> dict[str, dict]:
    path = credentials_path()
    if not path.exists():
        return {}
    _tighten_permissions(path)
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _tighten_permissions(path: Path) -> None:
    if os.name != "posix":
        return
    mode = path.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        path.chmod(0o600)


def _write_all(data: dict[str, dict]) -> None:
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        directory.chmod(0o700)

    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".credentials.")
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(data, handle, indent=2)
        if os.name == "posix":
            os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, credentials_path())
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def load(env_name: str) -> StoredCredentials | None:
    entry = _read_all().get(env_name)
    if not entry or not entry.get("refresh_token") or not entry.get("uid"):
        return None
    return StoredCredentials(**{k: entry.get(k) for k in StoredCredentials.__dataclass_fields__})


def save(env_name: str, creds: StoredCredentials) -> None:
    data = _read_all()
    data[env_name] = asdict(creds)
    _write_all(data)


def delete(env_name: str) -> bool:
    data = _read_all()
    if env_name not in data:
        return False
    del data[env_name]
    _write_all(data)
    return True
