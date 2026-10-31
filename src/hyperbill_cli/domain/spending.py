"""Spent / impressions totals, aggregated server-side exactly like the web tables."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ..core.context import AppContext


def totals(app: AppContext, owner: str, owner_id: str) -> dict[str, float]:
    parent = app.user_path(owner, owner_id)
    spent = app.firestore.aggregate(parent, "deviceSpending", {"spent": ("sum", "spent")})["spent"]
    impressions = app.firestore.aggregate(parent, "fulfillmentsNormalized", {"impressions": ("sum", "impressions")})
    return {"spent": spent, "impressions": impressions["impressions"]}


def attach_totals(app: AppContext, owner: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    app.session.id_token()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda row: totals(app, owner, row["id"]), rows))
    return [{**row, **result} for row, result in zip(rows, results)]
