"""Hyperbill CLI entry point.

Every command prints JSON to stdout. Failures print ``{"error": {...}}`` to
stderr with a stable ``code`` and a non-zero exit status.
"""

from __future__ import annotations

import sys

import click

from . import __version__
from .commands.account import conditions_group, dashboard_cmd, wallet_group
from .commands.auth import auth_group
from .commands.campaigns import campaigns_group
from .commands.devices import devices_group
from .commands.media import media_group
from .commands.webhooks import webhooks_group
from .core.config import ENVIRONMENTS
from .core.context import AppContext
from .core.errors import EXIT_USAGE, HyperbillError
from .core.output import emit_error


class JsonErrorGroup(click.Group):
    def main(self, *args, **kwargs):
        kwargs["standalone_mode"] = False
        try:
            return super().main(*args, **kwargs)
        except HyperbillError as error:
            emit_error(error)
            sys.exit(error.exit_code)
        except click.exceptions.Abort:
            emit_error(HyperbillError("Aborted", code="aborted"))
            sys.exit(1)
        except click.ClickException as error:
            emit_error(HyperbillError(error.format_message(), code="invalid_input"))
            sys.exit(EXIT_USAGE)
        except click.exceptions.Exit as exit_:
            sys.exit(exit_.exit_code)


@click.group(cls=JsonErrorGroup)
@click.option("--env", "env_name", type=click.Choice(list(ENVIRONMENTS)), envvar="HYPERBILL_ENV",
              help="Target environment (default: prod).")
@click.version_option(__version__, prog_name="hyperbill")
@click.pass_context
def cli(ctx: click.Context, env_name: str | None) -> None:
    """Hyperbill for AI agents: book billboards, run campaigns and webhooks, manage media."""
    ctx.obj = AppContext(env_name)


for command in (auth_group, devices_group, campaigns_group, webhooks_group, media_group,
                wallet_group, dashboard_cmd, conditions_group):
    cli.add_command(command)
