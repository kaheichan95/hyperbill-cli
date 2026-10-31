from datetime import datetime, timezone

from hyperbill_cli.core import firestore_values as values
from hyperbill_cli.core.firestore import Doc, _decode_cursor, _encode_cursor
from hyperbill_cli.core.config import resolve_environment
from hyperbill_cli.domain.fulfillment_csv import to_csv
from hyperbill_cli.domain.media import storage_path


def test_value_roundtrip():
    data = {"a": 1, "b": 1.5, "c": "x", "d": [True, None], "e": {"f": "g"}}
    assert values.decode_fields(values.encode_fields(data)) == data


def test_timestamp_encoding_is_utc():
    encoded = values.encode(datetime(2026, 1, 1, 8, tzinfo=timezone.utc))
    assert encoded == {"timestampValue": "2026-01-01T08:00:00Z"}


def test_cursor_roundtrip():
    doc = Doc(id="c1", name="projects/p/databases/(default)/documents/users/u/campaigns/c1",
              data={}, raw={"createdAt": {"timestampValue": "2026-01-01T00:00:00Z"}})
    assert _decode_cursor(_encode_cursor(doc, "createdAt")) == [
        {"timestampValue": "2026-01-01T00:00:00Z"},
        {"referenceValue": doc.name},
    ]


def test_storage_path_matches_web_scheme():
    assert storage_path("u", "ad.final.mp4") == "u/media/ad.final.mp4"
    assert storage_path("u", "noext") == "u/media/noext.noext"


def test_csv_flattens_frames_and_strips_bbox():
    csv = to_csv([{
        "id": "f1",
        "bidPrice": 1.2,
        "context": {"features": [{"time": "09:00", "weekday": "monday",
                                  "persons": [{"age": 30, "bbox": {"x1": 1}}], "animals": [{"label": "dog"}]}]},
    }])
    header, row = csv.split("\n")
    assert header.startswith('"id","bidPrice","context.time","context.weekday"')
    assert "bbox" not in header
    assert '"dog"' in row


def test_insecure_base_url_rejected(monkeypatch):
    monkeypatch.setenv("HYPERBILL_BASE_URL", "http://example.com")
    try:
        resolve_environment("prod")
    except Exception as exc:  # noqa: BLE001
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("expected rejection")
