from __future__ import annotations

import click

from ..core import paste_login
from ..core.context import AppContext, pass_app
from ..core.output import emit
from ..domain import auth


@click.group("auth")
def auth_group() -> None:
    """Sign in, sign out and show the current user."""


@auth_group.command("login")
@click.option("--email", help="Sign in with email + password instead of the browser (password is prompted).")
@click.option("--no-browser", is_flag=True, help="Print the login URL instead of opening a browser.")
@click.option("--paste/--no-paste", default=None,
              help="Sign in from a browser on another machine by pasting a code back. Default: on over SSH.")
@pass_app
def login(app: AppContext, email: str | None, no_browser: bool, paste: bool | None) -> None:
    """Sign in as yourself. Run this once, interactively; agents reuse the session."""
    if email:
        password = click.prompt("Password", hide_input=True, err=True)
        emit(auth.login_with_password(app, email, password))
    else:
        if paste is None:
            paste = paste_login.is_remote_session()
        emit(auth.login_with_browser(app, open_browser=not no_browser, paste=paste))


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
