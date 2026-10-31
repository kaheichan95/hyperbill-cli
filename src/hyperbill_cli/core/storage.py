"""Firebase Storage REST client acting as the signed-in user (storage rules apply)."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO
from urllib.parse import quote

import requests

from .errors import HyperbillError
from .session import Session

UPLOAD_TIMEOUT_SECONDS = 600
TIMEOUT_SECONDS = 60
CHUNK_BYTES = 1024 * 1024


class StorageClient:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.base = f"https://firebasestorage.googleapis.com/v0/b/{session.env.storage_bucket}/o"

    def upload(self, path: str, stream: BinaryIO, content_type: str) -> dict:
        response = self._request(
            "POST",
            self.base,
            params={"uploadType": "media", "name": path},
            headers={"Content-Type": content_type},
            data=stream,
            timeout=UPLOAD_TIMEOUT_SECONDS,
        )
        return response.json()

    def delete(self, path: str) -> bool:
        response = self._request("DELETE", self._object_url(path), allow_404=True)
        return response is not None

    def download_url(self, path: str) -> str:
        """Equivalent of the web SDK's ``getDownloadURL`` (a long-lived, shareable link)."""
        metadata = self._request("GET", self._object_url(path)).json()
        token = (metadata.get("downloadTokens") or "").split(",")[0]
        if not token:
            raise HyperbillError(f"No download token for {path}", code="not_found", status=404)
        return f"{self._object_url(path)}?alt=media&token={token}"

    def download(self, path: str, destination: Path) -> int:
        response = self._request("GET", self._object_url(path), params={"alt": "media"}, stream=True)
        written = 0
        with destination.open("wb") as handle:
            for chunk in response.iter_content(CHUNK_BYTES):
                handle.write(chunk)
                written += len(chunk)
        return written

    def _object_url(self, path: str) -> str:
        return f"{self.base}/{quote(path, safe='')}"

    def _request(self, method: str, url: str, allow_404: bool = False, **kwargs) -> requests.Response | None:
        kwargs.setdefault("timeout", TIMEOUT_SECONDS)
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Firebase {self.session.id_token()}"
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
        except requests.RequestException as exc:
            raise HyperbillError(f"Could not reach Firebase Storage: {exc}", code="network_error") from exc
        if allow_404 and response.status_code == 404:
            return None
        if not response.ok:
            code = {401: "not_authenticated", 403: "forbidden", 404: "not_found"}.get(response.status_code, "storage_error")
            raise HyperbillError(f"Storage request failed (HTTP {response.status_code})", code=code, status=response.status_code)
        return response
