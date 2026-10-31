"""Date/time parsing for CLI inputs. Naive inputs use the machine's local zone, like the web UI."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from ..core.errors import invalid_input

TIME_RANGES = ("1H", "24H", "7D", "28D", "3M")


def parse_datetime(text: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise invalid_input(f"Invalid date/time '{text}'. Use ISO 8601, e.g. 2026-10-20T09:00+08:00") from exc
    return parsed if parsed.tzinfo else parsed.astimezone()


def to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_day(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise invalid_input(f"Invalid date '{text}'. Use YYYY-MM-DD") from exc


def local_day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min).astimezone()
    end = datetime.combine(day, time(23, 59, 59, 999000)).astimezone()
    return start, end


def days_ago(days: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)
