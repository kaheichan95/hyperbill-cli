"""Campaigns: reads go to Firestore, writes go through the web API's validation."""

from __future__ import annotations

from typing import Any

from ..core.context import AppContext
from ..core.errors import invalid_input, not_found
from . import spending

STATUSES = ("live", "paused", "suspended", "terminated", "completed")
SORT_FIELDS = ("createdAt", "name", "startDate", "endDate", "status", "totalBudget")
MIN_PLAY_SECONDS = 5
MAX_PLAY_SECONDS = 120


def list_campaigns(app: AppContext, statuses: list[str], sort: str, descending: bool, limit: int,
                   page_token: str | None, with_totals: bool) -> dict[str, Any]:
    filters = [("status", "in", statuses)] if statuses and set(statuses) != set(STATUSES) else []
    page = app.firestore.query(app.user_path(), "campaigns", filters, order_by=sort,
                               descending=descending, limit=limit, page_token=page_token)
    rows = [doc.as_dict() for doc in page.docs]
    if with_totals:
        rows = spending.attach_totals(app, "campaigns", rows)
    return {"campaigns": rows, "nextPageToken": page.next_page_token}


def get_campaign(app: AppContext, campaign_id: str, with_totals: bool = True) -> dict[str, Any]:
    doc = app.firestore.get(app.user_path("campaigns", campaign_id))
    if not doc:
        raise not_found(f"Campaign {campaign_id} not found")
    campaign = doc.as_dict()
    if with_totals:
        campaign.update(spending.totals(app, "campaigns", campaign_id))
    return campaign


def _check_play_duration(value: float | None) -> None:
    if value is not None and not MIN_PLAY_SECONDS <= value <= MAX_PLAY_SECONDS:
        raise invalid_input(f"Play duration must be between {MIN_PLAY_SECONDS} and {MAX_PLAY_SECONDS} seconds")


def create_campaign(app: AppContext, payload: dict[str, Any]) -> dict[str, Any]:
    required = ["name", "totalBudget", "perSecondPrice", "startDate", "endDate", "activeDuration", "mediaFileId", "deviceIds"]
    missing = [key for key in required if payload.get(key) in (None, "", [])]
    if missing:
        raise invalid_input(f"Missing required fields: {', '.join(missing)}")
    _check_play_duration(payload["activeDuration"])
    return app.api.json("POST", "/api/campaigns", json=payload)


def duplicate_payload(app: AppContext, source_id: str) -> dict[str, Any]:
    """Fields the web's 'duplicate campaign' flow carries over."""
    source = get_campaign(app, source_id, with_totals=False)
    keys = ["name", "totalBudget", "perSecondPrice", "startDate", "endDate", "activeDuration",
            "mediaFileId", "deviceIds", "ctaUrl", "biddingLogic"]
    payload = {key: source[key] for key in keys if source.get(key) is not None}
    payload["name"] = f"{payload.get('name', 'Campaign')} (copy)"
    return payload


def update_campaign(app: AppContext, campaign_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    if not changes:
        raise invalid_input("Nothing to update")
    _check_play_duration(changes.get("activeDuration"))
    return app.api.json("PUT", f"/api/campaigns/{campaign_id}", json=changes)


def delete_campaign(app: AppContext, campaign_id: str) -> dict[str, Any]:
    return app.api.json("DELETE", f"/api/campaigns/{campaign_id}")


def performance(app: AppContext, campaign_id: str, time_range: str) -> dict[str, Any]:
    campaign = get_campaign(app, campaign_id, with_totals=False)
    body = {
        "deviceIds": campaign.get("deviceIds") or [],
        "campaignId": campaign_id,
        "biddingLogic": campaign.get("biddingLogic"),
        "activeDuration": round(campaign.get("activeDuration") or 0),
        "timeRange": time_range,
    }
    return app.api.json("POST", "/api/analytics/campaign-stats", json=body)


def simulate(app: AppContext, device_ids: list[str], bid_price: float, active_duration: float,
             bidding_logic: dict[str, Any] | None, time_range: str, campaign_id: str | None) -> dict[str, Any]:
    if not device_ids:
        raise invalid_input("At least one device id is required")
    if bid_price <= 0 or active_duration <= 0:
        raise invalid_input("Bid price and active duration must be positive")
    body = {
        "bidPrice": bid_price,
        "biddingLogic": bidding_logic,
        "deviceIds": device_ids,
        "activeDuration": round(active_duration),
        "timeRange": time_range,
        "campaignId": campaign_id,
    }
    return app.api.json("POST", "/api/analytics/simulate", json=body)
