from __future__ import annotations

import click

from ..core.context import AppContext, pass_app
from ..core.output import emit
from ..domain import auth


@click.group("auth")
def auth_group() -> None:
    """Sign in, sign out and show the current user."""


@auth_group.command("login")
@click.option("--email", help="Sign in with email + password instead of the browser (password is prompted).")
@click.option("--no-browser", is_flag=True, help="Print the login URL instead of opening a browser.")
@pass_app
def login(app: AppContext, email: str | None, no_browser: bool) -> None:
    """Sign in as yourself. Run this once, interactively; agents reuse the session."""
    if email:
        password = click.prompt("Password", hide_input=True, err=True)
        emit(auth.login_with_password(app, email, password))
    else:
        emit(auth.login_with_browser(app, open_browser=not no_browser))


@auth_group.command("logout")
@pass_app
def logout(app: AppContext) -> None:
    """Forget the stored session on this machine."""
    emit(auth.logout(app))


@auth_group.command("whoami")
@pass_app
def whoami(app: AppContext) -> None:
    """Show the signed-in account."""
    emit(auth.whoami(app))
