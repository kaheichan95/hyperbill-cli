"""Media library: upload, list, download and delete ad creatives."""

from __future__ import annotations

import json
import mimetypes
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..core.context import AppContext
from ..core.errors import HyperbillError, invalid_input, not_found
from . import mcc

MAX_UPLOAD_BYTES = 200 * 1024 * 1024
MIN_VIDEO_SECONDS = 5
MAX_VIDEO_SECONDS = 120
MODERATION_TIMEOUT_SECONDS = 180
FINISHED_CAMPAIGN_STATUSES = {"terminated", "completed"}


def storage_path(uid: str, filename: str) -> str:
    """Byte-for-byte the web's path scheme, including its quirk for extensionless names."""
    extension = filename.split(".")[-1]
    stem = re.sub(r"\.[^/.]+$", "", filename)
    return f"{uid}/media/{stem}.{extension}"


def list_media(app: AppContext, search: str | None, sort: str, descending: bool) -> list[dict[str, Any]]:
    order_by = sort if sort in {"filename", "uploadedAt"} else None
    docs = app.firestore.query_all(app.user_path(), "media", order_by=order_by, descending=descending)
    items = [doc.as_dict() for doc in docs]
    if search:
        items = [m for m in items if search.lower() in (m.get("filename") or "").lower()]
    if sort == "duration":
        items.sort(key=lambda m: m.get("duration") or 0, reverse=descending)
    return items


def get_media(app: AppContext, media_id: str) -> dict[str, Any]:
    doc = app.firestore.get(app.user_path("media", media_id))
    if not doc:
        raise not_found(f"Media {media_id} not found")
    return doc.as_dict()


def _content_type(path: Path, override: str | None) -> str:
    content_type = override or mimetypes.guess_type(path.name)[0] or ""
    if not content_type.startswith(("image/", "video/")):
        raise invalid_input(f"Only images and videos can be uploaded (detected '{content_type or 'unknown'}')")
    return content_type


def _video_duration(path: Path, override: float | None) -> float:
    if override is not None:
        return override
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise invalid_input("Could not determine video duration: install ffprobe or pass --duration")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=False,
    )
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise invalid_input("Could not read video duration; pass --duration") from exc


def upload(app: AppContext, path: Path, merchant_category_code: str, name: str | None,
           content_type: str | None, duration: float | None) -> dict[str, Any]:
    if not path.is_file():
        raise invalid_input(f"{path} is not a file")
    size = path.stat().st_size
    if size > MAX_UPLOAD_BYTES:
        raise invalid_input("File size must be 200 MB or less")

    filename = Path(name or path.name).name
    mime = _content_type(Path(filename), content_type)
    mcc.require_code(merchant_category_code)

    record: dict[str, Any] = {
        "filename": filename,
        "contentType": mime,
        "size": size,
        "uploadedAt": datetime.now(timezone.utc),
        "suspend": "Pending Review",
        "merchantCategoryCode": merchant_category_code,
    }
    if mime.startswith("video/"):
        seconds = _video_duration(path, duration)
        if not MIN_VIDEO_SECONDS <= seconds <= MAX_VIDEO_SECONDS:
            raise invalid_input(f"Video must be between {MIN_VIDEO_SECONDS} and {MAX_VIDEO_SECONDS} seconds")
        record["duration"] = seconds

    duplicates = app.firestore.query(app.user_path(), "media", [("filename", "==", filename)], limit=1)
    if duplicates.docs:
        raise HyperbillError(f'A file named "{filename}" already exists. Rename it before uploading.',
                             code="conflict", details={"existingMediaId": duplicates.docs[0].id})

    with path.open("rb") as stream:
        app.storage.upload(storage_path(app.uid, filename), stream, mime)
    doc = app.firestore.create(app.user_path("media"), record)

    return {"id": doc.id, **doc.data, "moderation": moderate(app, doc.id)}


def moderate(app: AppContext, media_id: str) -> str:
    """``PASS`` clears the review flag; anything else is the suspension reason."""
    try:
        response = app.api.json("POST", "/api/media/moderate", json={"mediaId": media_id},
                                timeout=MODERATION_TIMEOUT_SECONDS)
        return response.get("result", "pending")
    except HyperbillError:
        return "pending"


def campaigns_using(app: AppContext, media_id: str) -> list[dict[str, Any]]:
    docs = app.firestore.query_all(app.user_path(), "campaigns", [("mediaFileId", "==", media_id)])
    return [
        {"id": d.id, "name": d.data.get("name"), "status": d.data.get("status")}
        for d in docs if d.data.get("status") not in FINISHED_CAMPAIGN_STATUSES
    ]


def delete(app: AppContext, media_id: str) -> dict[str, Any]:
    item = get_media(app, media_id)
    in_use = campaigns_using(app, media_id)
    if in_use:
        raise HyperbillError("Cannot delete: media is used by active campaigns", code="conflict",
                             details={"campaigns": in_use})
    app.storage.delete(storage_path(app.uid, item["filename"]))
    app.firestore.delete(app.user_path("media", media_id))
    return {"deleted": media_id}


def download(app: AppContext, media_id: str, destination: Path | None) -> dict[str, Any]:
    item = get_media(app, media_id)
    target = destination or Path(item["filename"])
    if target.is_dir():
        target = target / item["filename"]
    size = app.storage.download(storage_path(app.uid, item["filename"]), target)
    return {"file": str(target), "bytes": size}


def share_url(app: AppContext, media_id: str) -> dict[str, Any]:
    item = get_media(app, media_id)
    return {"id": media_id, "url": app.storage.download_url(storage_path(app.uid, item["filename"]))}
