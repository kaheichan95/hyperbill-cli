from __future__ import annotations

from pathlib import Path

import click

from ..core.context import AppContext, pass_app
from ..core.output import emit
from ..domain import mcc, media
from .options import confirm_destructive


@click.group("media")
def media_group() -> None:
    """Upload and manage ad creatives (images and 5-120s videos, max 200 MB)."""


@media_group.command("list")
@click.option("--search", help="Case-insensitive filename filter.")
@click.option("--sort", type=click.Choice(["uploadedAt", "filename", "duration"]), default="uploadedAt", show_default=True)
@click.option("--asc", is_flag=True)
@pass_app
def list_cmd(app: AppContext, search: str | None, sort: str, asc: bool) -> None:
    """List media. `suspend` is set while pending review or when rejected."""
    emit(media.list_media(app, search, sort, not asc))


@media_group.command("get")
@click.argument("media_id")
@pass_app
def get_cmd(app: AppContext, media_id: str) -> None:
    """Show one media item."""
    emit(media.get_media(app, media_id))


@media_group.command("upload")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--mcc", "mcc_code", required=True, help="Merchant category code of the advertised business.")
@click.option("--name", help="Filename to store as (default: local filename). Must be unique.")
@click.option("--content-type", help="Override the detected MIME type.")
@click.option("--duration", type=float, help="Video length in seconds (auto-detected with ffprobe).")
@pass_app
def upload_cmd(app: AppContext, file: Path, mcc_code: str, name: str | None,
               content_type: str | None, duration: float | None) -> None:
    """Upload a file and run content moderation. Usable in campaigns once moderation is PASS."""
    emit(media.upload(app, file, mcc_code, name, content_type, duration))


@media_group.command("moderate")
@click.argument("media_id")
@pass_app
def moderate_cmd(app: AppContext, media_id: str) -> None:
    """Re-run moderation for a media item still pending review."""
    emit({"id": media_id, "moderation": media.moderate(app, media_id)})


@media_group.command("download")
@click.argument("media_id")
@click.option("--out", type=click.Path(path_type=Path), help="File or directory (default: ./<filename>).")
@pass_app
def download_cmd(app: AppContext, media_id: str, out: Path | None) -> None:
    """Download the original file."""
    emit(media.download(app, media_id, out))


@media_group.command("url")
@click.argument("media_id")
@pass_app
def url_cmd(app: AppContext, media_id: str) -> None:
    """Long-lived shareable download link (anyone holding it can fetch the file)."""
    emit(media.share_url(app, media_id))


@media_group.command("delete")
@click.argument("media_id")
@click.option("--yes", is_flag=True, help="Confirm permanent deletion.")
@pass_app
def delete_cmd(app: AppContext, media_id: str, yes: bool) -> None:
    """Delete media not used by any active campaign."""
    confirm_destructive(yes, "delete media")
    emit(media.delete(app, media_id))


@media_group.command("mcc")
@click.option("--search", help="Match category name or code.")
def mcc_cmd(search: str | None) -> None:
    """List merchant category codes for --mcc."""
    emit(mcc.search(search))
