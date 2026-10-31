import base64
import json

import pytest

from hyperbill_cli.core.errors import HyperbillError
from hyperbill_cli.core.paste_login import decode_paste_code, is_remote_session


def _encode(payload: dict) -> str:
    """Same encoding as ``pasteCode`` in hyperbill-web: unpadded base64url JSON."""
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")


def test_decodes_code_for_matching_state():
    code = _encode({"s": "state-1", "t": "refresh-abc"})
    assert decode_paste_code(f"  {code[:10]}\n{code[10:]} ", "state-1") == "refresh-abc"


@pytest.mark.parametrize("code", [
    _encode({"s": "other-state", "t": "refresh-abc"}),
    _encode({"s": "state-1", "t": ""}),
    _encode({"s": "state-1"}),
    "not base64 !!",
])
def test_rejects_bad_codes(code):
    with pytest.raises(HyperbillError):
        decode_paste_code(code, "state-1")


def test_detects_ssh(monkeypatch):
    monkeypatch.delenv("SSH_CONNECTION", raising=False)
    monkeypatch.delenv("SSH_TTY", raising=False)
    assert not is_remote_session()
    monkeypatch.setenv("SSH_CONNECTION", "1.2.3.4 5 6.7.8.9 22")
    assert is_remote_session()
