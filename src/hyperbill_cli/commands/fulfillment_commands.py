"""``fulfillments`` / ``export`` subcommands shared by campaigns and webhooks."""

from __future__ import annotations

from pathlib import Path

import click

from ..core.context import AppContext, pass_app
from ..core.output import emit
from ..domain import fulfillment_csv, fulfillments
from ..domain.timeutil import parse_day
from .options import paginated


def add_fulfillment_commands(group: click.Group, owner: str, noun: str) -> None:
    @group.command("fulfillments")
    @click.argument("owner_id", metavar=f"{noun.upper()}_ID")
    @click.option("--date", "day", help="Only this local day (YYYY-MM-DD).")
    @paginated
    @pass_app
    def list_cmd(app: AppContext, owner_id: str, day: str | None, limit: int, page_token: str | None) -> None:
        """Won plays, newest first, with the audience context at play time."""
        emit(fulfillments.list_page(app, owner, owner_id, parse_day(day) if day else None, limit, page_token))

    @group.command("export")
    @click.argument("owner_id", metavar=f"{noun.upper()}_ID")
    @click.option("--date", "day", help="Only this local day (YYYY-MM-DD).")
    @click.option("--out", type=click.Path(dir_okay=False, path_type=Path), required=True, help="CSV file to write.")
    @pass_app
    def export_cmd(app: AppContext, owner_id: str, day: str | None, out: Path) -> None:
        """Export every fulfillment to CSV (same columns as the web download)."""
        rows = fulfillments.list_all(app, owner, owner_id, parse_day(day) if day else None)
        out.write_text(fulfillment_csv.to_csv(rows), encoding="utf-8")
        emit({"file": str(out), "rows": len(rows)})
