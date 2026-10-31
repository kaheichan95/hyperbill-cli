"""Fulfillment logs (won plays) for a campaign or webhook."""

from __future__ import annotations

from datetime import date
from typing import Any

from ..core.context import AppContext
from ..core.firestore import Filter
from .timeutil import local_day_bounds

COLLECTION = "fulfillmentsNormalized"


def _filters(day: date | None) -> list[Filter]:
    if not day:
        return []
    start, end = local_day_bounds(day)
    return [("timestamp", ">=", start), ("timestamp", "<=", end)]


def list_page(app: AppContext, owner: str, owner_id: str, day: date | None, limit: int,
              page_token: str | None) -> dict[str, Any]:
    page = app.firestore.query(
        app.user_path(owner, owner_id), COLLECTION, _filters(day),
        order_by="timestamp", descending=True, limit=limit, page_token=page_token,
    )
    return {"fulfillments": [d.as_dict() for d in page.docs], "nextPageToken": page.next_page_token}


def list_all(app: AppContext, owner: str, owner_id: str, day: date | None) -> list[dict[str, Any]]:
    docs = app.firestore.query_all(
        app.user_path(owner, owner_id), COLLECTION, _filters(day), order_by="timestamp", descending=True,
    )
    return [d.as_dict() for d in docs]
