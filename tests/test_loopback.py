import re
import threading
import time

import pytest
import requests

from hyperbill_cli.core import loopback
from hyperbill_cli.core.config import ENVIRONMENTS


@pytest.fixture
def login(monkeypatch):
    opened = {}
    monkeypatch.setattr(loopback.webbrowser, "open", lambda url: opened.setdefault("url", url))
    result = {}

    def run():
        try:
            result["token"] = loopback.browser_login(ENVIRONMENTS["prod"])
        except Exception as exc:  # noqa: BLE001
            result["error"] = exc

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    while "url" not in opened:
        time.sleep(0.02)
    port, state = re.search(r"port=(\d+)&state=([\w-]+)", opened["url"]).groups()
    yield f"http://127.0.0.1:{port}/callback", state, thread, result


def test_rejects_wrong_state_and_origin_then_accepts_valid(login):
    url, state, thread, result = login
    assert requests.post(url, data={"state": "x" * 43, "refresh_token": "t"}).status_code == 400
    assert requests.post(url, data={"state": state, "refresh_token": "t"},
                         headers={"Origin": "https://evil.example"}).status_code == 403
    assert requests.get(url).status_code == 404
    ok = requests.post(url, data={"state": state, "refresh_token": "good"},
                       headers={"Origin": "https://hyperbill.co"})
    assert ok.status_code == 200
    thread.join(5)
    assert result["token"] == "good"


def test_confirmation_code_format():
    assert re.fullmatch(r"[0-9A-F]{4}-[0-9A-F]{4}", loopback.confirmation_code("abc"))
    assert loopback.confirmation_code("abcDEF123_-xyzabcDEF123_-xyzabcDEF12") == "C61A-9383"
