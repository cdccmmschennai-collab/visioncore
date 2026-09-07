"""Shared Batch/BatchItem/TagImage creation.

Used by both the multipart `/batches/upload` and `/batches/batch-process`
endpoints (`app/api/v1/batches.py`), so a tag entering the system either way
goes through the exact same de-duplication and storage logic before
extraction ever begins — no separate ingestion path to keep in sync.
"""
from __future__ import annotations

from pathlib import Path
from typing import OrderedDict

from sqlalchemy import select

from app.models import Activity, ActivityAction, AssetTag, Batch, BatchItem, BatchStatus, ItemStatus, TagImage
from app.services.storage import resolve_stored, stream_upload

_MEDIA_BY_EXT = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".jfif": "image/jpeg",
    ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp",
}


async def create_batch_with_items(
    db,
    reference: str,
    grouped: "OrderedDict[str, dict]",
    user,
    *,
    is_batch_process: bool = False,
) -> tuple[Batch, list[AssetTag]]:
    """Create one Batch plus one BatchItem (and its TagImages) per entry.

    `grouped` maps tag_number -> {"description": str, "files": [(filename, UploadFile), ...]}.
    Returns the created Batch and the AssetTag rows found to already exist
    (marked DUPLICATE on the batch rather than re-extracted) — same semantics
    the `/batches/upload` endpoint has always had.
    """
    batch = Batch(
        reference=reference,
        user_id=user.id,
        status=BatchStatus.UPLOADED,
        total_images=sum(len(g["files"]) for g in grouped.values()),
        total_tags=len(grouped),
        is_batch_process=is_batch_process,
    )
    db.add(batch)
    await db.flush()

    duplicates: list[AssetTag] = []

    for tag_number, group in grouped.items():
        existing = await db.scalar(select(AssetTag).where(AssetTag.tag_number == tag_number))

        item = BatchItem(
            batch_id=batch.id,
            tag_number=tag_number,
            description=group["description"],
            status=ItemStatus.DUPLICATE if existing else ItemStatus.UPLOADED,
            error_message="Tag already extracted" if existing else None,
            asset_tag_id=existing.id if existing else None,
        )
        db.add(item)
        await db.flush()

        for original_name, upload_file in group["files"]:
            # Streamed straight to disk in chunks (never the whole file in
            # memory at once — see storage.stream_upload) under its own
            # collision-proof UUID path, hashing as it goes.
            stored, content_hash, size_bytes = await stream_upload(
                reference, tag_number, original_name, upload_file
            )
            await upload_file.close()
            stored_path, suffix = str(stored), stored.suffix

            # Same bytes already stored somewhere (any batch, any tag) — point
            # this row at that file instead of keeping a second copy, and
            # drop the copy we just streamed. A row pulled in by
            # app/services/sync_client.py can carry a stored_path whose file
            # was never actually fetched down here — reusing that dangling
            # path would silently drop the bytes we were just handed, so
            # fall back to the copy we just wrote when it doesn't resolve.
            duplicate = await db.scalar(
                select(TagImage.stored_path).where(TagImage.content_hash == content_hash).limit(1)
            )
            if duplicate is not None:
                try:
                    resolve_stored(duplicate)
                    stored.unlink(missing_ok=True)
                    stored_path, suffix = duplicate, Path(duplicate).suffix
                except (FileNotFoundError, ValueError):
                    pass

            db.add(TagImage(
                item_id=item.id,
                original_filename=original_name,
                stored_path=stored_path,
                content_hash=content_hash,
                media_type=_MEDIA_BY_EXT.get(suffix.lower(), "image/jpeg"),
                size_bytes=size_bytes,
            ))

        if existing:
            duplicates.append(existing)
            db.add(Activity(
                user_id=user.id, action=ActivityAction.DUPLICATE_BLOCKED,
                tag_number=tag_number, description=group["description"],
                detail="Tag already extracted — existing record shown",
            ))
        else:
            # One row per tag, mirroring Extract/Edit/Download, so History (and
            # "View Photos") can show this tag's number/description directly
            # instead of a batch-wide summary.
            db.add(Activity(
                user_id=user.id, action=ActivityAction.UPLOAD,
                tag_number=tag_number, description=group["description"],
                detail=f"Uploaded {len(group['files'])} image(s)"
                       + (" via Batch Process" if is_batch_process else ""),
                meta={"batch_reference": reference, "batch_id": batch.id, "item_id": item.id},
            ))

    await db.commit()
    return batch, duplicates
