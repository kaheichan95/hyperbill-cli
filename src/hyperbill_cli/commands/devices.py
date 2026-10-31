from __future__ import annotations

from pathlib import Path

import click

from ..core.context import AppContext, pass_app
from ..core.output import emit
from ..domain import devices
from ..domain.timeutil import days_ago, parse_datetime
from .options import split_ids


@click.group("devices")
def devices_group() -> None:
    """Find billboards and inspect their bid-price statistics."""


@devices_group.command("list")
@click.option("--region", default="HK", show_default=True, help="ISO 3166-2 principal subdivision.")
@click.option("--district", help="Exact district name (see `devices locations`).")
@click.option("--locality", help="Exact locality name.")
@click.option("--vision/--no-vision", default=None, help="Only devices with / without audience vision.")
@click.option("--all", "include_all", is_flag=True, help="Include offline and whitelist-restricted devices.")
@pass_app
def list_cmd(app: AppContext, region: str, district: str | None, locality: str | None,
             vision: bool | None, include_all: bool) -> None:
    """List devices you can book (online and open to you)."""
    emit(devices.list_devices(app, region, district, locality, vision, include_all))


@devices_group.command("get")
@click.argument("device_id")
@pass_app
def get_cmd(app: AppContext, device_id: str) -> None:
    """Show one device, including location, screen and opening hours."""
    emit(devices.get_device(app, device_id))


@devices_group.command("stats")
@click.argument("device_ids", nargs=-1, required=True)
@click.option("--days", type=click.FloatRange(0.01, 90), default=7, show_default=True)
@click.option("--start", help="ISO start time (overrides --days).")
@click.option("--end", help="ISO end time (default: now).")
@click.option("--bucket", type=click.Choice(["hour", "day"]), default="hour", show_default=True)
@click.option("--campaign", "campaign_id", help="Only fulfillments of this campaign.")
@click.option("--webhook", "webhook_id", help="Only fulfillments of this webhook.")
@pass_app
def stats_cmd(app: AppContext, device_ids: tuple[str, ...], days: float, start: str | None, end: str | None,
              bucket: str, campaign_id: str | None, webhook_id: str | None) -> None:
    """Fulfillment count and price percentiles (mean/p90/p95/p99 per second) over time."""
    start_at = parse_datetime(start) if start else days_ago(days)
    end_at = parse_datetime(end) if end else days_ago(0)
    emit(devices.bid_statistics(app, split_ids(device_ids), start_at, end_at, bucket, campaign_id, webhook_id))


@devices_group.command("images")
@click.argument("device_id")
@click.option("--out", "out_dir", type=click.Path(file_okay=False, path_type=Path), default=Path("."))
@pass_app
def images_cmd(app: AppContext, device_id: str, out_dir: Path) -> None:
    """Download the device's site photos."""
    emit(devices.download_images(app, device_id, out_dir))


@devices_group.command("locations")
@click.option("--region", default="HK", show_default=True)
@pass_app
def locations_cmd(app: AppContext, region: str) -> None:
    """Districts and localities usable as --district / --locality filters."""
    emit(devices.locations(app, region))
