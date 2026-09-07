"""Filesystem layout for uploads and generated workbooks.

    <STORAGE_DIR>/uploads/<batch_ref>/<tag_number>/<uuid>.<ext>
    <STORAGE_DIR>/exports/<tag_number>/AI Output-<stem>.xlsx
    <STORAGE_DIR>/exports/<tag_number>/<stem>-Template.xlsx

Paths are always resolved and checked against the storage root before use, so a
crafted tag number cannot escape the directory via `../`.
"""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from app.core.config import settings
from app.services.filename_parser import safe_filename

#: Chunk size for stream_upload's copy loop — bounds peak memory to roughly
#: one chunk per file in flight, regardless of how large the file itself is.
_STREAM_CHUNK_BYTES = 1024 * 1024


def storage_root() -> Path:
    root = Path(settings.storage_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _within_root(path: Path) -> Path:
    root = storage_root()
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Resolved path escapes the storage root")
    return resolved


def upload_dir(batch_reference: str, tag_number: str) -> Path:
    path = storage_root() / "uploads" / safe_filename(batch_reference) / safe_filename(tag_number)
    path = _within_root(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_dir(tag_number: str) -> Path:
    path = storage_root() / "exports" / safe_filename(tag_number)
    path = _within_root(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def stream_upload(
    batch_reference: str, tag_number: str, filename: str, upload_file
) -> tuple[Path, str, int]:
    """Copy an UploadFile straight to its permanent location in bounded
    chunks, computing its SHA-256 hash and size along the way.

    Stored under a UUID so two photos with the same name cannot collide —
    same naming convention the old byte-buffering save_upload used. Unlike
    reading the whole file into memory first, this never holds more than one
    chunk at a time, which is what keeps a many-tag Batch Process upload from
    needing the entire batch resident in memory at once.
    """
    suffix = Path(filename).suffix.lower() or ".jpg"
    target = upload_dir(batch_reference, tag_number) / f"{uuid.uuid4().hex}{suffix}"
    hasher = hashlib.sha256()
    size = 0
    await upload_file.seek(0)
    with target.open("wb") as out:
        while chunk := await upload_file.read(_STREAM_CHUNK_BYTES):
            out.write(chunk)
            hasher.update(chunk)
            size += len(chunk)
    return target, hasher.hexdigest(), size


def ai_output_name(stem: str) -> str:
    return safe_filename(f"AI Output-{stem}.xlsx")


def template_output_name(stem: str) -> str:
    return safe_filename(f"{stem}-Template.xlsx")


def write_export(tag_number: str, filename: str, data: bytes) -> Path:
    target = export_dir(tag_number) / safe_filename(filename)
    target.write_bytes(data)
    return target


def local_path_for(path_str: str) -> Path:
    """Re-anchor a stored_path DB value onto this environment's storage root.

    stored_path is saved as an absolute path baked in on whichever machine
    created the row (see stream_upload/write_export above/below). A row pulled in by
    app/services/sync_client.py from another environment still carries
    *that* environment's absolute path — different OS, different install
    directory — which never lives under this machine's storage root. Rebuild
    it from its position under 'uploads' or 'exports', the only two
    subtrees a stored_path is ever under, so it resolves correctly no matter
    which environment originally wrote it.
    """
    parts = Path(path_str.replace("\\", "/")).parts
    for anchor in ("uploads", "exports"):
        if anchor in parts:
            return storage_root().joinpath(*parts[parts.index(anchor):])
    return storage_root() / Path(path_str).name


def resolve_stored(path_str: str) -> Path:
    """Validate a path read back from the database before serving it."""
    path = _within_root(local_path_for(path_str))
    if not path.is_file():
        raise FileNotFoundError(path_str)
    return path


def remove_files(path_strs: list[str]) -> None:
    """Best-effort cleanup after a DB delete — a file that's already missing
    (or was never written) must never fail the request that already
    committed the database change.
    """
    for path_str in path_strs:
        try:
            resolve_stored(path_str).unlink()
        except (FileNotFoundError, ValueError, OSError):
            continue
