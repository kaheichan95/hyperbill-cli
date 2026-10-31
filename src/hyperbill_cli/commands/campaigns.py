from __future__ import annotations

from typing import Any

import click

from ..core.context import AppContext, pass_app
from ..core.output import emit
from ..domain import campaigns, conditions
from ..domain.timeutil import parse_datetime, to_iso
from .fulfillment_commands import add_fulfillment_commands
from .options import confirm_destructive, paginated, put_if_set, split_ids, time_range_option

CONDITION_HELP = "Bidding condition JSON, @file.json, or 'none'. See `hyperbill conditions schema`."


@click.group("campaigns")
def campaigns_group() -> None:
    """Create and manage fixed-price campaigns."""


@campaigns_group.command("list")
@click.option("--status", "statuses", multiple=True, type=click.Choice(campaigns.STATUSES))
@click.option("--sort", type=click.Choice(campaigns.SORT_FIELDS), default="createdAt", show_default=True)
@click.option("--asc", is_flag=True, help="Ascending order (default newest first).")
@click.option("--no-totals", is_flag=True, help="Skip spent/impressions aggregation (faster).")
@paginated
@pass_app
def list_cmd(app: AppContext, statuses: tuple[str, ...], sort: str, asc: bool, no_totals: bool,
             limit: int, page_token: str | None) -> None:
    """List campaigns with spent and impressions."""
    emit(campaigns.list_campaigns(app, list(statuses), sort, not asc, limit, page_token, not no_totals))


@campaigns_group.command("get")
@click.argument("campaign_id")
@pass_app
def get_cmd(app: AppContext, campaign_id: str) -> None:
    """Show a campaign with spent and impressions."""
    emit(campaigns.get_campaign(app, campaign_id))


def _fields(name, budget, price, start, end, duration, media_id, devices, cta_url, condition, status) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    put_if_set(payload, "name", name)
    put_if_set(payload, "totalBudget", budget)
    put_if_set(payload, "perSecondPrice", price)
    put_if_set(payload, "startDate", to_iso(parse_datetime(start)) if start else None)
    put_if_set(payload, "endDate", to_iso(parse_datetime(end)) if end else None)
    put_if_set(payload, "activeDuration", duration)
    put_if_set(payload, "mediaFileId", media_id)
    put_if_set(payload, "ctaUrl", cta_url)
    put_if_set(payload, "biddingLogic", conditions.load_bidding_logic(condition))
    put_if_set(payload, "status", status)
    if devices:
        payload["deviceIds"] = split_ids(devices)
    return payload


def campaign_field_options(func):
    options = [
        click.option("--name"),
        click.option("--budget", type=click.FloatRange(min=0, min_open=True), help="Total budget in the device currency."),
        click.option("--price", type=click.FloatRange(min=0, min_open=True), help="Price per second of play."),
        click.option("--start", help="ISO start, e.g. 2026-10-20T09:00+08:00 (naive = local time)."),
        click.option("--end", help="ISO end."),
        click.option("--duration", type=click.FloatRange(5, 120), help="Seconds per play (5-120)."),
        click.option("--media", "media_id", help="Media id from `hyperbill media list`."),
        click.option("--device", "devices", multiple=True, help="Device id; repeat or comma-separate."),
        click.option("--cta-url", help="URL encoded in the on-screen QR code ('' to remove)."),
        click.option("--condition", help=CONDITION_HELP),
    ]
    for option in reversed(options):
        func = option(func)
    return func


@campaigns_group.command("create")
@campaign_field_options
@click.option("--status", type=click.Choice(["live", "paused"]), default="live", show_default=True)
@click.option("--from", "source_id", help="Copy settings from an existing campaign, then apply overrides.")
@pass_app
def create_cmd(app: AppContext, name, budget, price, start, end, duration, media_id, devices, cta_url,
               condition, status, source_id) -> None:
    """Create a campaign. Fails with code insufficient_funds if the wallet can't cover the budget."""
    payload = campaigns.duplicate_payload(app, source_id) if source_id else {}
    payload.update(_fields(name, budget, price, start, end, duration, media_id, devices, cta_url, condition, status))
    emit(campaigns.create_campaign(app, payload))


@campaigns_group.command("update")
@click.argument("campaign_id")
@campaign_field_options
@click.option("--status", type=click.Choice(["live", "paused", "terminated"]))
@pass_app
def update_cmd(app: AppContext, campaign_id, name, budget, price, start, end, duration, media_id, devices,
               cta_url, condition, status) -> None:
    """Change any campaign field; only the options you pass are updated."""
    changes = _fields(name, budget, price, start, end, duration, media_id, devices, cta_url, condition, status)
    emit(campaigns.update_campaign(app, campaign_id, changes))


@campaigns_group.command("pause")
@click.argument("campaign_id")
@pass_app
def pause_cmd(app: AppContext, campaign_id: str) -> None:
    """Stop bidding without losing settings."""
    emit(campaigns.update_campaign(app, campaign_id, {"status": "paused"}))


@campaigns_group.command("resume")
@click.argument("campaign_id")
@pass_app
def resume_cmd(app: AppContext, campaign_id: str) -> None:
    """Set a paused campaign live again (re-checks wallet balance)."""
    emit(campaigns.update_campaign(app, campaign_id, {"status": "live"}))


@campaigns_group.command("terminate")
@click.argument("campaign_id")
@click.option("--yes", is_flag=True, help="Confirm: terminated campaigns can't be edited again.")
@pass_app
def terminate_cmd(app: AppContext, campaign_id: str, yes: bool) -> None:
    """End a campaign permanently."""
    confirm_destructive(yes, "terminate a campaign")
    emit(campaigns.update_campaign(app, campaign_id, {"status": "terminated"}))


@campaigns_group.command("delete")
@click.argument("campaign_id")
@click.option("--yes", is_flag=True, help="Confirm permanent deletion.")
@pass_app
def delete_cmd(app: AppContext, campaign_id: str, yes: bool) -> None:
    """Delete a campaign permanently."""
    confirm_destructive(yes, "delete a campaign")
    emit(campaigns.delete_campaign(app, campaign_id))


@campaigns_group.command("stats")
@click.argument("campaign_id")
@time_range_option
@pass_app
def stats_cmd(app: AppContext, campaign_id: str, time_range: str) -> None:
    """Actual performance: views, impressions, spend, coverage, demographics."""
    emit(campaigns.performance(app, campaign_id, time_range))


@campaigns_group.command("simulate")
@click.option("--device", "devices", multiple=True, required=True)
@click.option("--price", type=float, required=True, help="Bid price per second.")
@click.option("--duration", type=click.FloatRange(5, 120), required=True)
@click.option("--condition", help=CONDITION_HELP)
@click.option("--campaign", "campaign_id", help="Compare against an existing campaign.")
@time_range_option
@pass_app
def simulate_cmd(app: AppContext, devices, price, duration, condition, campaign_id, time_range) -> None:
    """Estimate how a bid would have performed over past traffic."""
    logic = conditions.load_bidding_logic(condition)
    emit(campaigns.simulate(app, split_ids(devices), price, duration, logic, time_range, campaign_id))


add_fulfillment_commands(campaigns_group, owner="campaigns", noun="campaign")
