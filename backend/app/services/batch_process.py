"""Batch Process: scan a fixed local folder of tag subfolders and run every
one of them through the existing extraction pipeline (`app.services.pipeline`)
— no separate extraction implementation.

    <BATCH_PROCESS_SOURCE_DIR>\\<TAG-NAME>\\*.jpg           (scanned)
    <BATCH_PROCESS_SOURCE_DIR>\\AI Extraction\\AI Extraction_<TAG-NAME>.xlsx
    <BATCH_PROCESS_SOURCE_DIR>\\Consolidate file\\Consolidated_<batch reference>.xlsx

Only a Batch created through `start_batch_process` (Batch.is_batch_process)
ever touches these two output folders — a normal drag-and-drop upload is
completely unaffected.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models import AssetTag, Batch, BatchItem, ItemStatus
from app.services.download_links import ai_excel_download_url, photo_view_url
from app.services.excel_template import build_template_workbook
from app.services.filename_parser import (
    SUPPORTED_EXTENSIONS,
    excel_basename,
    parse_filename,
    parse_folder_name,
    safe_filename,
)
from app.services.pipeline import process_batch, reextract_item, template_path_columns
from app.services.storage import resolve_stored

logger = logging.getLogger(__name__)

_RESERVED_DIR_NAMES = {"ai extraction", "consolidate file"}


def _source_root() -> Path:
    return Path(settings.batch_process_source_dir)


def _ai_extraction_dir() -> Path:
    return _source_root() / "AI Extraction"


def _consolidate_dir() -> Path:
    return _source_root() / "Consolidate file"


class BatchProcessError(Exception):
    """Raised for problems the caller should see as a 4xx, e.g. a missing folder."""


def scan_tag_folders() -> list[tuple[str, str, list[tuple[str, bytes]]]]:
    """Discover every tag under the Batch Process source folder.

    A tag can be either a subfolder (`<TAG>-<DESCRIPTION>\\*.jpg`, parsed via
    `parse_folder_name` — for a tag with several photos) or one or more loose
    `<TAG>-<DESCRIPTION>.jpg` files dropped directly in the source folder
    (parsed via `parse_filename`). This mirrors exactly the two ways the
    existing "upload a folder or loose files" Dropzone flow already accepts
    photos — see `parse_filename`/`parse_folder_name` in `upload()`.

    Returns one (tag_number, description, [(filename, bytes), ...]) tuple per
    tag with at least one supported image. Anything that fails to parse, or a
    folder with no images, is skipped and logged rather than aborting the
    whole scan — the rest of the ~50 tags must still get processed.
    """
    root = _source_root()
    if not root.is_dir():
        raise BatchProcessError(f"Batch Process folder not found: {root}")

    grouped: "dict[str, dict]" = {}

    for entry in sorted(root.iterdir()):
        if entry.name.strip().lower() in _RESERVED_DIR_NAMES:
            continue

        if entry.is_dir():
            parsed = parse_folder_name(entry.name)
            if not parsed.ok:
                logger.warning("Batch Process: skipping folder %r (%s)", entry.name, parsed.reason)
                continue
            group = grouped.setdefault(parsed.tag_number, {"description": parsed.description, "files": []})
            before = len(group["files"])
            for file_path in sorted(entry.iterdir()):
                if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue
                if len(group["files"]) >= settings.max_images_per_tag:
                    break
                group["files"].append((file_path.name, file_path.read_bytes()))
            if len(group["files"]) == before:
                logger.warning("Batch Process: skipping folder %r (no images found)", entry.name)
            continue

        if entry.is_file() and entry.suffix.lower() in SUPPORTED_EXTENSIONS:
            parsed = parse_filename(entry.name)
            if not parsed.ok:
                logger.warning("Batch Process: skipping file %r (%s)", entry.name, parsed.reason)
                continue
            group = grouped.setdefault(parsed.tag_number, {"description": parsed.description, "files": []})
            if len(group["files"]) < settings.max_images_per_tag:
                group["files"].append((entry.name, entry.read_bytes()))

    return [
        (tag_number, group["description"], group["files"])
        for tag_number, group in grouped.items()
        if group["files"]
    ]


def _export_ai_excel(asset_tag: AssetTag, folder_stem: str) -> None:
    """Copy this tag's already-generated AI Output workbook into the Batch
    Process "AI Extraction" folder, named `AI Extraction_<tag-name>.xlsx`.

    Best-effort: a filesystem hiccup here must not undo an extraction that
    already succeeded and is safely recorded in the database and the normal
    exports directory.
    """
    if not asset_tag.ai_excel_path:
        return
    try:
        source = resolve_stored(asset_tag.ai_excel_path)
    except (FileNotFoundError, ValueError):
        logger.warning("Batch Process: AI workbook missing on disk for %s", asset_tag.tag_number)
        return
    try:
        target_dir = _ai_extraction_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / safe_filename(f"AI Extraction_{folder_stem}.xlsx")
        shutil.copyfile(source, target)
    except OSError:
        logger.exception("Batch Process: could not save AI Extraction copy for %s", asset_tag.tag_number)


async def _export_completed_items(batch_id: int) -> None:
    """Copy every tag in this batch that has a result — freshly COMPLETED or
    an already-extracted DUPLICATE — into the AI Extraction folder, so every
    scanned tag folder ends up represented on disk exactly once.
    """
    async with AsyncSessionLocal() as session:
        batch = await session.scalar(
            select(Batch)
            .options(selectinload(Batch.items).selectinload(BatchItem.asset_tag))
            .where(Batch.id == batch_id)
        )
        if batch is None:
            return
        for item in batch.items:
            if item.status in (ItemStatus.COMPLETED, ItemStatus.DUPLICATE) and item.asset_tag:
                _export_ai_excel(item.asset_tag, excel_basename(item.tag_number, item.description))


async def _write_consolidated(batch_id: int) -> None:
    """(Re)build the one consolidated workbook for this Batch Process run.

    Overwrites the same file every time (named after the batch's own
    reference) rather than creating a new one, so re-extracting a failed tag
    later just updates this file in place — never a second, stale copy.
    """
    async with AsyncSessionLocal() as session:
        batch = await session.scalar(
            select(Batch)
            .options(
                selectinload(Batch.items).selectinload(BatchItem.asset_tag),
                selectinload(Batch.items).selectinload(BatchItem.images),
            )
            .where(Batch.id == batch_id)
        )
        if batch is None:
            return

        records = []
        for item in batch.items:
            if item.status not in (ItemStatus.COMPLETED, ItemStatus.DUPLICATE) or item.asset_tag is None:
                continue
            tag = item.asset_tag
            photo_names = [img.original_filename for img in item.images] or [f"{tag.tag_number}.jpg"]
            input_cell, output_cell = template_path_columns(tag.tag_number, tag.description, photo_names)
            records.append({
                "payload": tag.final_payload,
                "ai_payload": tag.ai_payload,
                "input_photos": input_cell,
                "output_file": output_cell,
                "ai_excel_url": ai_excel_download_url(tag.tag_number),
                "input_photo_url": photo_view_url(tag.tag_number),
            })

        if not records:
            return

        content = build_template_workbook(records)
        reference = batch.reference

    try:
        target_dir = _consolidate_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / safe_filename(f"Consolidated_{reference}.xlsx")
        target.write_bytes(content)
    except OSError:
        logger.exception("Batch Process: could not write consolidated workbook for %s", reference)


async def run_batch_process(batch_id: int, user_id: int) -> None:
    """Run every pending tag in a Batch Process batch, then mirror the
    results into the AI Extraction and Consolidate file folders.

    Extraction itself is exactly `process_batch` (same pipeline a normal
    upload uses) — this only adds the two folder exports around it.
    """
    await process_batch(batch_id, user_id)
    await _export_completed_items(batch_id)
    await _write_consolidated(batch_id)


async def reextract_batch_process_item(item_id: int, batch_id: int, user_id: int) -> None:
    """Re-extract one failed tag from a Batch Process batch, then refresh
    that tag's AI Extraction copy and the batch's consolidated workbook.

    Extraction itself is exactly `reextract_item` — same as a normal batch's
    "Re-Extract" button.
    """
    await reextract_item(item_id, batch_id, user_id)
    await _export_completed_items(batch_id)
    await _write_consolidated(batch_id)
