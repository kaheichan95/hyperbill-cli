"""Account-wide headline numbers shown on the web dashboard."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..core.context import AppContext


def summary(app: AppContext, since: datetime) -> dict[str, Any]:
    cost = app.api.json("GET", "/api/dashboard/average-cost", params={"from": int(since.timestamp() * 1000)})
    campaigns = app.api.json("GET", "/api/dashboard/active-campaigns")
    webhooks = app.api.json("GET", "/api/dashboard/active-webhooks")
    return {
        "since": since.isoformat(),
        "impressions": cost.get("impressions", 0),
        "cpm": cost.get("cpm", 0),
        "activeCampaigns": campaigns.get("activeCampaigns", 0),
        "activeWebhooks": webhooks.get("activeWebhooks", 0),
    }
