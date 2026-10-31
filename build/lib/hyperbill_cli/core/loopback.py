"""Browser login via a one-shot loopback listener (RFC 8252 style).

The CLI binds 127.0.0.1 on a random port, opens ``/cli/login`` on the
Hyperbill site, and waits for the page to POST back a freshly minted Firebase
refresh token together with the unguessable ``state`` it was given.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode

import click

from .config import Environment
from .errors import HyperbillError

LOGIN_TIMEOUT_SECONDS = 300
MAX_BODY_BYTES = 16 * 1024

_DONE_PAGE = (
    b"<!doctype html><meta charset=utf-8><title>Hyperbill CLI</title>"
    b"<body style='font-family:sans-serif;text-align:center;margin-top:20vh'>"
    b"<h2>Hyperbill CLI is signed in.</h2><p>You can close this window.</p></body>"
)


def confirmation_code(state: str) -> str:
    """Must match ``confirmationCode`` in hyperbill-web ``lib/auth/cli-session.ts``."""
    digest = hashlib.sha256(state.encode()).hexdigest()[:8].upper()
    return f"{digest[:4]}-{digest[4:]}"


class _Result:
    def __init__(self) -> None:
        self.refresh_token: str | None = None
        self.done = threading.Event()


def _make_handler(state: str, expected_origin: str, result: _Result) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        timeout = 10  # browsers open idle speculative connections; don't let them linger

        def do_POST(self) -> None:  # noqa: N802 - http.server API
            if self.path != "/callback" or result.done.is_set():
                self._reply(404, b"Not found")
                return

            origin = self.headers.get("Origin")
            if origin is not None and origin != expected_origin:
                self._reply(403, b"Unexpected origin")
                return

            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY_BYTES:
                self._reply(400, b"Bad request")
                return

            form = parse_qs(self.rfile.read(length).decode("utf-8", "replace"))
            sent_state = (form.get("state") or [""])[0]
            token = (form.get("refresh_token") or [""])[0]
            if not hmac.compare_digest(sent_state, state) or not token:
                self._reply(400, b"Login state mismatch. Restart `hyperbill auth login`.")
                return

            result.refresh_token = token
            result.done.set()
            self._reply(200, _DONE_PAGE, content_type="text/html; charset=utf-8")

        def do_GET(self) -> None:  # noqa: N802
            self._reply(404, b"Not found")

        def _reply(self, status: int, body: bytes, content_type: str = "text/plain; charset=utf-8") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # silence request logging
            return

    return Handler


def browser_login(env: Environment, open_browser: bool = True) -> str:
    """Run the loopback flow and return the refresh token."""
    state = secrets.token_urlsafe(32)
    result = _Result()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(state, env.origin, result))
    server.daemon_threads = True
    port = server.server_address[1]

    url = f"{env.base_url}/en/cli/login?{urlencode({'port': port, 'state': state})}"
    click.echo(f"Confirmation code: {confirmation_code(state)}", err=True)
    click.echo(f"Open this URL to sign in (it must show the same code):\n  {url}", err=True)
    if open_browser:
        webbrowser.open(url)

    serving = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.5}, daemon=True)
    serving.start()
    try:
        result.done.wait(LOGIN_TIMEOUT_SECONDS)
    finally:
        server.shutdown()
        server.server_close()

    if not result.refresh_token:
        raise HyperbillError("Timed out waiting for browser sign-in", code="login_timeout")
    return result.refresh_token
