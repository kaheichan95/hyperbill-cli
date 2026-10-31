"""Browser login for remote machines, where the browser can't reach a loopback listener.

The CLI opens ``/cli/login?mode=paste`` with a random ``state``. After the user
authorizes, the page shows a code bundling that ``state`` with a fresh refresh
token; the user pastes it back here and the CLI checks the ``state`` matches.
"""

from __future__ import annotations

import base64
import binascii
import hmac
import json
import os
import secrets
from urllib.parse import urlencode

import click

from .config import Environment
from .errors import HyperbillError
from .loopback import confirmation_code


def is_remote_session() -> bool:
    return bool(os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"))


def decode_paste_code(code: str, state: str) -> str:
    """Must match ``pasteCode`` in hyperbill-web ``lib/auth/cli-session.ts``."""
    code = "".join(code.split())
    try:
        payload = json.loads(base64.urlsafe_b64decode(code + "=" * (-len(code) % 4)))
        sent_state, token = payload["s"], payload["t"]
    except (binascii.Error, ValueError, KeyError, TypeError):
        raise HyperbillError("That code is not a Hyperbill CLI login code", code="login_failed") from None
    if not isinstance(sent_state, str) or not hmac.compare_digest(sent_state, state):
        raise HyperbillError("That code belongs to a different login. Restart `hyperbill auth login`.",
                             code="login_failed")
    if not isinstance(token, str) or not token:
        raise HyperbillError("That code has no session in it", code="login_failed")
    return token


def paste_login(env: Environment) -> str:
    """Run the copy-paste flow and return the refresh token."""
    state = secrets.token_urlsafe(32)
    url = f"{env.base_url}/en/cli/login?{urlencode({'mode': 'paste', 'state': state})}"
    click.echo(f"Confirmation code: {confirmation_code(state)}", err=True)
    click.echo(f"Open this URL in any browser to sign in (it must show the same code):\n  {url}", err=True)
    code = click.prompt("Paste the code shown after you authorize", hide_input=True, err=True)
    return decode_paste_code(code, state)
