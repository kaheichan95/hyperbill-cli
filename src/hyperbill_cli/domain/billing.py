"""Read-only wallet and transaction history. Payment methods and top-up settings stay web-only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.context import AppContext


def wallet(app: AppContext) -> dict[str, Any]:
    data = app.api.json("GET", "/api/user/wallet")
    return {
        "balances": data.get("balances", {}),
        "autoRecharge": {
            "thresholds": data.get("rechargeThresholds", {}),
            "amounts": data.get("rechargeAmounts", {}),
        },
        "paymentMethods": [
            {k: pm.get(k) for k in ("brand", "last4", "isDefault")} for pm in data.get("paymentMethods", [])
        ],
    }


def transactions(app: AppContext, currency: str | None) -> list[dict[str, Any]]:
    params = {"currency": currency} if currency else None
    return app.api.json("GET", "/api/user/transactions", params=params).get("transactions", [])


def download_invoice(app: AppContext, transaction_id: str, destination: Path | None) -> dict[str, Any]:
    response = app.api.request("GET", f"/api/user/transactions/{transaction_id}/invoice")
    target = destination or Path(f"invoice-{transaction_id}.pdf")
    if target.is_dir():
        target = target / f"invoice-{transaction_id}.pdf"
    target.write_bytes(response.content)
    return {"file": str(target), "bytes": len(response.content)}
