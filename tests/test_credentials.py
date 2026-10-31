import stat

from hyperbill_cli.core import credentials


def test_saved_file_is_private(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPERBILL_CONFIG_DIR", str(tmp_path / "cfg"))
    credentials.save("prod", credentials.StoredCredentials(refresh_token="r", uid="u", email="e"))

    path = credentials.credentials_path()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert credentials.load("prod").uid == "u"
    assert credentials.load("dev") is None

    assert credentials.delete("prod") is True
    assert credentials.load("prod") is None
