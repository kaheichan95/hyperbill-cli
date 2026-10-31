"""Per-invocation container wiring the environment, session and clients together."""

from __future__ import annotations

from functools import cached_property

import click

from .config import Environment, resolve_environment
from .firestore import FirestoreClient
from .http import ApiClient
from .session import Session
from .storage import StorageClient


class AppContext:
    def __init__(self, env_name: str | None) -> None:
        self.env_name = env_name

    @cached_property
    def env(self) -> Environment:
        return resolve_environment(self.env_name)

    @cached_property
    def session(self) -> Session:
        return Session(self.env)

    @cached_property
    def api(self) -> ApiClient:
        return ApiClient(self.session)

    @cached_property
    def firestore(self) -> FirestoreClient:
        return FirestoreClient(self.session)

    @cached_property
    def storage(self) -> StorageClient:
        return StorageClient(self.session)

    @property
    def uid(self) -> str:
        return self.session.uid

    def user_path(self, *segments: str) -> str:
        return "/".join(["users", self.uid, *segments])


pass_app = click.make_pass_decorator(AppContext)
