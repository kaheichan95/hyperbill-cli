from __future__ import annotations

from typing import Any

import click

from ..core.context import AppContext, pass_app
from ..core.output import emit
from ..domain import webhooks
from .fulfillment_commands import add_fulfillment_commands
from .options import confirm_destructive, paginated, put_if_set, split_ids, time_range_option

show_token_option = click.option("--show-token", is_flag=True, help="Print the full endpoint auth token.")


@click.group("webhooks")
def webhooks_group() -> None:
    """Real-time bidding: Hyperbill calls your HTTPS endpoint with live audience context."""


@webhooks_group.command("list")
@click.option("--status", "statuses", multiple=True, type=click.Choice(webhooks.STATUSES))
@click.option("--sort", type=click.Choice(webhooks.SORT_FIELDS), default="createdAt", show_default=True)
@click.option("--asc", is_flag=True)
@click.option("--no-totals", is_flag=True, help="Skip spent/impressions aggregation.")
@show_token_option
@paginated
@pass_app
def list_cmd(app: AppContext, statuses, sort, asc, no_totals, show_token, limit, page_token) -> None:
    """List webhooks with spent and impressions (tokens masked)."""
    emit(webhooks.list_webhooks(app, list(statuses), sort, not asc, limit, page_token, not no_totals, show_token))


@webhooks_group.command("get")
@click.argument("webhook_id")
@show_token_option
@pass_app
def get_cmd(app: AppContext, webhook_id: str, show_token: bool) -> None:
    """Show one webhook (token masked unless --show-token)."""
    emit(webhooks.get_webhook(app, webhook_id, reveal_token=show_token))


def _fields(name, endpoint, devices, budget, status) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    put_if_set(payload, "name", name)
    put_if_set(payload, "endpoint", endpoint)
    put_if_set(payload, "totalBudget", budget)
    put_if_set(payload, "status", status)
    if devices:
        payload["deviceIds"] = split_ids(devices)
    return payload


def webhook_field_options(func):
    options = [
        click.option("--name"),
        click.option("--endpoint", help="HTTPS URL that receives bid requests."),
        click.option("--device", "devices", multiple=True, help="Device id; repeat or comma-separate."),
        click.option("--budget", type=click.FloatRange(min=0), help="Total budget in the device currency."),
    ]
    for option in reversed(options):
        func = option(func)
    return func


@webhooks_group.command("create")
@webhook_field_options
@click.option("--status", type=click.Choice(["test", "live", "paused"]), default="test", show_default=True,
              help="Start in 'test' to validate with `webhooks test` before going live.")
@show_token_option
@pass_app
def create_cmd(app: AppContext, name, endpoint, devices, budget, status, show_token) -> None:
    """Register a bidding endpoint. Defaults to 'test' status."""
    payload = _fields(name, endpoint, devices, budget, status)
    payload["version"] = "v1"
    emit(webhooks.create_webhook(app, payload, show_token))


@webhooks_group.command("update")
@click.argument("webhook_id")
@webhook_field_options
@click.option("--status", type=click.Choice(["test", "live", "paused", "terminated"]))
@show_token_option
@pass_app
def update_cmd(app: AppContext, webhook_id, name, endpoint, devices, budget, status, show_token) -> None:
    """Change any webhook field; only the options you pass are updated."""
    emit(webhooks.update_webhook(app, webhook_id, _fields(name, endpoint, devices, budget, status), show_token))


@webhooks_group.command("test")
@click.argument("webhook_id")
@click.option("--device", "device_id", required=True, help="Device id to put in the mock request.")
@pass_app
def test_cmd(app: AppContext, webhook_id: str, device_id: str) -> None:
    """Send a mock bid request to the endpoint (webhook must be in 'test' status) and validate the reply."""
    emit(webhooks.send_test(app, webhook_id, device_id))


@webhooks_group.command("delete")
@click.argument("webhook_id")
@click.option("--yes", is_flag=True, help="Confirm permanent deletion.")
@pass_app
def delete_cmd(app: AppContext, webhook_id: str, yes: bool) -> None:
    """Delete a webhook permanently."""
    confirm_destructive(yes, "delete a webhook")
    emit(webhooks.delete_webhook(app, webhook_id))


@webhooks_group.command("stats")
@click.argument("webhook_id")
@time_range_option
@pass_app
def stats_cmd(app: AppContext, webhook_id: str, time_range: str) -> None:
    """Fulfillments, impressions, spend and demographics."""
    emit(webhooks.performance(app, webhook_id, time_range))


add_fulfillment_commands(webhooks_group, owner="webhooks", noun="webhook")
