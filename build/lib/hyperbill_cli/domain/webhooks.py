"""Real-time bidding webhooks."""

from __future__ import annotations

from typing import Any

from ..core.context import AppContext
from ..core.errors import invalid_input, not_found
from . import spending

STATUSES = ("test", "live", "paused", "suspended", "terminated", "completed")
SORT_FIELDS = ("createdAt", "name", "status", "endpoint", "totalBudget")


def mask_token(webhook: dict[str, Any], reveal: bool) -> dict[str, Any]:
    """The token authenticates Hyperbill to the user's endpoint; keep it out of agent logs by default."""
    token = webhook.get("token")
    if token and not reveal:
        return {**webhook, "token": f"{token[:6]}…(hidden, use --show-token)"}
    return webhook


def list_webhooks(app: AppContext, statuses: list[str], sort: str, descending: bool, limit: int,
                  page_token: str | None, with_totals: bool, reveal_tokens: bool) -> dict[str, Any]:
    filters = [("status", "in", statuses)] if statuses and set(statuses) != set(STATUSES) else []
    page = app.firestore.query(app.user_path(), "webhooks", filters, order_by=sort,
                               descending=descending, limit=limit, page_token=page_token)
    rows = [mask_token(doc.as_dict(), reveal_tokens) for doc in page.docs]
    if with_totals:
        rows = spending.attach_totals(app, "webhooks", rows)
    return {"webhooks": rows, "nextPageToken": page.next_page_token}


def get_webhook(app: AppContext, webhook_id: str, reveal_token: bool = False, with_totals: bool = True) -> dict[str, Any]:
    doc = app.firestore.get(app.user_path("webhooks", webhook_id))
    if not doc:
        raise not_found(f"Webhook {webhook_id} not found")
    webhook = mask_token(doc.as_dict(), reveal_token)
    if with_totals:
        webhook.update(spending.totals(app, "webhooks", webhook_id))
    return webhook


def _check_endpoint(endpoint: str | None) -> None:
    if endpoint is not None and not endpoint.startswith("https://"):
        raise invalid_input("Endpoint URL must use HTTPS")


def create_webhook(app: AppContext, payload: dict[str, Any], reveal_token: bool) -> dict[str, Any]:
    if not payload.get("endpoint") or not payload.get("deviceIds"):
        raise invalid_input("endpoint and at least one device are required")
    _check_endpoint(payload["endpoint"])
    return mask_token(app.api.json("POST", "/api/webhooks", json=payload), reveal_token)


def update_webhook(app: AppContext, webhook_id: str, changes: dict[str, Any], reveal_token: bool) -> dict[str, Any]:
    if not changes:
        raise invalid_input("Nothing to update")
    _check_endpoint(changes.get("endpoint"))
    return mask_token(app.api.json("PUT", f"/api/webhooks/{webhook_id}", json=changes), reveal_token)


def delete_webhook(app: AppContext, webhook_id: str) -> dict[str, Any]:
    return app.api.json("DELETE", f"/api/webhooks/{webhook_id}")


def send_test(app: AppContext, webhook_id: str, device_id: str) -> dict[str, Any]:
    return app.api.json("POST", f"/api/webhooks/{webhook_id}/test", json={"deviceId": device_id})


def performance(app: AppContext, webhook_id: str, time_range: str) -> dict[str, Any]:
    webhook = get_webhook(app, webhook_id, with_totals=False)
    body = {"deviceIds": webhook.get("deviceIds") or [], "webhookId": webhook_id, "timeRange": time_range}
    return app.api.json("POST", "/api/analytics/webhook-stats", json=body)
