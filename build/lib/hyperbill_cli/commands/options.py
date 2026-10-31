"""Option parsing helpers shared by command groups."""

from __future__ import annotations

from typing import Iterable

import click

from ..domain.timeutil import TIME_RANGES


def split_ids(values: Iterable[str]) -> list[str]:
    """Accept both ``--device a --device b`` and ``--device a,b``."""
    ids: list[str] = []
    for value in values:
        ids.extend(part.strip() for part in value.split(",") if part.strip())
    return list(dict.fromkeys(ids))


def put_if_set(target: dict, key: str, value: object) -> None:
    if value is not None:
        target[key] = value


time_range_option = click.option(
    "--range", "time_range", type=click.Choice(TIME_RANGES), default="7D", show_default=True,
    help="Look-back window ending now.",
)

pagination_options = [
    click.option("--limit", type=click.IntRange(1, 500), default=25, show_default=True),
    click.option("--page-token", help="nextPageToken from a previous call."),
]


def paginated(func):
    for option in reversed(pagination_options):
        func = option(func)
    return func


def confirm_destructive(yes: bool, what: str) -> None:
    if not yes:
        raise click.UsageError(f"Refusing to {what} without --yes")
