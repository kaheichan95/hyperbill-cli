"""Billboard devices: discovery, eligibility, images and bid-price statistics."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.context import AppContext
from ..core.errors import invalid_input, not_found
from .timeutil import to_iso


def _with_eligibility(device: dict[str, Any], uid: str) -> dict[str, Any]:
    whitelist = device.get("whitelistUserIds") or []
    online = device.get("status") != "offline"
    whitelisted = not whitelist or uid in whitelist
    device.pop("whitelistUserIds", None)
    return {
        **device,
        "vision": bool(device.get("vision", False)),
        "online": online,
        "whitelisted": whitelisted,
        "bookable": online and whitelisted,
    }


def list_devices(
    app: AppContext,
    subdivision: str,
    district: str | None = None,
    locality: str | None = None,
    vision: bool | None = None,
    include_unbookable: bool = False,
) -> list[dict[str, Any]]:
    docs = app.firestore.query_all("", "devices", [("location.principalSubdivision", "==", subdivision)])
    devices = [_with_eligibility(doc.as_dict(), app.uid) for doc in docs]

    def keep(device: dict[str, Any]) -> bool:
        location = device.get("location") or {}
        if district and location.get("district") != district:
            return False
        if locality and location.get("locality") != locality:
            return False
        if vision is not None and device["vision"] != vision:
            return False
        return include_unbookable or device["bookable"]

    return sorted(filter(keep, devices), key=lambda d: d["id"])


def get_device(app: AppContext, device_id: str) -> dict[str, Any]:
    doc = app.firestore.get(f"devices/{device_id}")
    if not doc:
        raise not_found(f"Device {device_id} not found")
    return _with_eligibility(doc.as_dict(), app.uid)


def bid_statistics(
    app: AppContext,
    device_ids: list[str],
    start: datetime,
    end: datetime,
    bucket: str,
    campaign_id: str | None = None,
    webhook_id: str | None = None,
) -> dict[str, Any]:
    if not device_ids:
        raise invalid_input("At least one device id is required")
    body: dict[str, Any] = {"deviceIds": device_ids, "start": to_iso(start), "end": to_iso(end), "bucket": bucket}
    if campaign_id:
        body["campaignId"] = campaign_id
    if webhook_id:
        body["webhookId"] = webhook_id
    return app.api.json("POST", "/api/analytics/percentiles", json=body)


def download_images(app: AppContext, device_id: str, out_dir: Path) -> list[dict[str, Any]]:
    device = get_device(app, device_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for filename in device.get("images") or []:
        safe_name = Path(filename).name
        destination = out_dir / safe_name
        size = app.storage.download(f"device/{device_id}/{filename}", destination)
        saved.append({"file": str(destination), "bytes": size})
    return saved


def locations(app: AppContext, code: str) -> dict[str, Any]:
    return app.api.json("GET", f"/api/locations/{code}", authenticated=False)
