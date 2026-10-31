"""Read-only account views: dashboard, wallet, transactions, invoices, targeting schema."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from pathlib import Path

import click

from ..core.context import AppContext, pass_app
from ..core.output import emit
from ..domain import billing, condition_schema, dashboard, conditions
from ..domain.timeutil import parse_datetime

HORIZONS = ("1D", "1W", "1M", "3M")


def _horizon_start(horizon: str) -> datetime:
    now = datetime.now().astimezone()
    if horizon == "1D":
        return now - timedelta(days=1)
    start_of_today = datetime.combine(now.date(), time.min).astimezone()
    if horizon == "1W":
        return start_of_today - timedelta(days=7)
    months = 1 if horizon == "1M" else 3
    month_index = start_of_today.month - 1 - months
    year, month = start_of_today.year + month_index // 12, month_index % 12 + 1
    return start_of_today.replace(year=year, month=month, day=min(start_of_today.day, 28))


@click.command("dashboard")
@click.option("--horizon", type=click.Choice(HORIZONS), default="1W", show_default=True)
@click.option("--since", help="ISO start time (overrides --horizon).")
@pass_app
def dashboard_cmd(app: AppContext, horizon: str, since: str | None) -> None:
    """Impressions, CPM and active campaign/webhook counts."""
    emit(dashboard.summary(app, parse_datetime(since) if since else _horizon_start(horizon)))


@click.group("wallet")
def wallet_group() -> None:
    """Balances and transaction history (read-only; manage payments on the website)."""


@wallet_group.command("balance")
@pass_app
def balance_cmd(app: AppContext) -> None:
    """Balance per currency, auto-recharge settings and saved card summary."""
    emit(billing.wallet(app))


@wallet_group.command("transactions")
@click.option("--currency", help="e.g. HKD")
@pass_app
def transactions_cmd(app: AppContext, currency: str | None) -> None:
    """Latest 50 transactions."""
    emit(billing.transactions(app, currency.upper() if currency else None))


@wallet_group.command("invoice")
@click.argument("transaction_id")
@click.option("--out", type=click.Path(path_type=Path), help="File or directory for the PDF.")
@pass_app
def invoice_cmd(app: AppContext, transaction_id: str, out: Path | None) -> None:
    """Download the PDF invoice of a successful top-up."""
    emit(billing.download_invoice(app, transaction_id, out))


@click.group("conditions")
def conditions_group() -> None:
    """Targeting conditions used by campaigns (--condition)."""


@conditions_group.command("schema")
def schema_cmd() -> None:
    """Fields, operators, allowed values and an example AST."""
    emit(condition_schema.describe())


@conditions_group.command("validate")
@click.argument("condition")
def validate_cmd(condition: str) -> None:
    """Validate a condition (inline JSON or @file.json) without sending it."""
    emit({"valid": True, "biddingLogic": conditions.load_bidding_logic(condition)})
