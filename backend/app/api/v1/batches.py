"""Upload, status polling, editing and workbook download."""
from __future__ import annotations

import html
import os
import secrets
from collections import OrderedDict
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.models import (
    AssetTag,
    Batch,
    BatchItem,
    BatchStatus,
    ItemStatus,
    TagImage,
    UserRole,
)
from app.schemas.common import Page
from app.schemas.tag import (
    AssetTagOut,
    BatchItemOut,
    BatchOut,
    ExtractedImageOut,
    ImageOut,
    RejectedFile,
    SaveTagRequest,
    UploadResponse,
)
from app.services.batch_ingest import create_batch_with_items
from app.services.batch_process import BatchProcessError, reextract_batch_process_item, run_batch_process, scan_tag_folders
from app.services.claude_extractor import ALLOWED_MEDIA_TYPES
from app.services.download_links import verify_photo_token
from app.services.fields import normalise_payload
from app.services.filename_parser import (
    SUPPORTED_EXTENSIONS,
    excel_basename,
    parse_filename,
    parse_folder_name,
    safe_filename,
)
from app.services.pipeline import generate_workbooks, process_batch, reextract_item
from app.services.storage import ai_output_name, resolve_stored, template_output_name
from app.services.sync_client import fetch_missing_photo

router = APIRouter(prefix="/batches", tags=["batches"])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _asset_tag_out(tag: AssetTag | None) -> AssetTagOut | None:
    if tag is None:
        return None
    out = AssetTagOut.model_validate(tag)
    out.has_ai_excel = bool(tag.ai_excel_path)
    out.has_template_excel = bool(tag.template_excel_path)
    return out


def _item_out(item: BatchItem) -> BatchItemOut:
    out = BatchItemOut(
        id=item.id,
        tag_number=item.tag_number,
        description=item.description,
        status=item.status,
        error_message=item.error_message,
        images=[ImageOut.model_validate(i) for i in item.images],
        asset_tag=_asset_tag_out(item.asset_tag),
        is_duplicate=item.status == ItemStatus.DUPLICATE,
    )
    return out


def _batch_out(batch: Batch) -> BatchOut:
    return BatchOut(
        id=batch.id,
        reference=batch.reference,
        status=batch.status,
        total_images=batch.total_images,
        total_tags=batch.total_tags,
        created_at=batch.created_at,
        items=[_item_out(i) for i in batch.items],
    )


async def _load_batch(db, batch_id: int, user) -> Batch:
    batch = await db.scalar(
        select(Batch)
        .options(
            selectinload(Batch.items).selectinload(BatchItem.images),
            selectinload(Batch.items).selectinload(BatchItem.asset_tag),
        )
        .where(Batch.id == batch_id)
    )
    if batch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That batch no longer exists.")
    if batch.user_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "That batch belongs to another user.")
    return batch


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload(
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    folders: list[str] | None = Form(None),
) -> UploadResponse:
    """Accept up to 20 images, group them by tag, and start extraction.

    Files that cannot be parsed are rejected individually and reported back —
    one bad filename should not cost the user the other nineteen uploads.

    `folders` is an optional, positionally-parallel list to `files`: when a
    user uploads a folder tree instead of loose images, the frontend sends
    each file's immediate parent subfolder name here (empty string for a file
    picked without a folder). A non-empty entry groups that image by its
    subfolder (via `parse_folder_name`) instead of by its filename, so an
    entire subfolder of 1-5 photos becomes one tag regardless of how its
    individual files are named.
    """
    if not files:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Add at least one image.")
    if len(files) > settings.max_images_per_batch:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"A batch takes up to {settings.max_images_per_batch} images. "
            f"You selected {len(files)}.",
        )

    rejected: list[RejectedFile] = []
    grouped: OrderedDict[str, dict] = OrderedDict()
    max_bytes = settings.max_image_size_mb * 1024 * 1024

    for index, upload_file in enumerate(files):
        folder = folders[index] if folders and index < len(folders) else ""

        # Folder uploads are grouped by folder name, not filename, but a
        # non-image file (Thumbs.db, .DS_Store, desktop.ini) sitting in an
        # otherwise valid tag folder must still be rejected rather than
        # silently sent to the AI extractor as a photo.
        ext = os.path.splitext(upload_file.filename or "")[1].lower()
        if folder and ext not in SUPPORTED_EXTENSIONS:
            rejected.append(RejectedFile(
                filename=upload_file.filename or "(unnamed)",
                reason=f"Unsupported file type '{ext or 'none'}'",
            ))
            continue

        parsed = parse_folder_name(folder) if folder else parse_filename(upload_file.filename or "")
        if not parsed.ok:
            rejected.append(RejectedFile(filename=upload_file.filename or "(unnamed)",
                                         reason=parsed.reason))
            continue

        data = await upload_file.read()
        if not data:
            rejected.append(RejectedFile(filename=upload_file.filename, reason="File is empty"))
            continue
        if len(data) > max_bytes:
            rejected.append(RejectedFile(
                filename=upload_file.filename,
                reason=f"Larger than the {settings.max_image_size_mb} MB limit",
            ))
            continue

        group = grouped.setdefault(
            parsed.tag_number,
            {"description": parsed.description, "files": []},
        )
        if len(group["files"]) >= settings.max_images_per_tag:
            rejected.append(RejectedFile(
                filename=upload_file.filename,
                reason=f"Tag {parsed.tag_number} already has "
                       f"{settings.max_images_per_tag} images",
            ))
            continue
        group["files"].append((upload_file.filename, data))

    if len(grouped) > settings.max_tags_per_batch:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"A batch covers up to {settings.max_tags_per_batch} tags. "
            f"Your selection has {len(grouped)}.",
        )
    if not grouped:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "None of those files could be read. Names must look like "
            "12-4020-BV-0074-BALL VALVE.jpg",
        )

    reference = f"B-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(3).upper()}"
    batch, duplicate_tags = await create_batch_with_items(db, reference, grouped, user)
    duplicates = [_asset_tag_out(t) for t in duplicate_tags]

    duplicate_numbers = {t.tag_number for t in duplicate_tags}
    if any(tag_number not in duplicate_numbers for tag_number in grouped):
        background.add_task(process_batch, batch.id, user.id)

    batch = await _load_batch(db, batch.id, user)
    return UploadResponse(batch=_batch_out(batch), rejected=rejected, duplicates=duplicates)


@router.post("/batch-process", response_model=BatchOut, status_code=status.HTTP_201_CREATED)
async def batch_process(
    user: CurrentUser, db: DbSession, background: BackgroundTasks
) -> BatchOut:
    """Scan the Batch Process source folder and extract every tag subfolder
    found there through the same pipeline `upload()` uses above.

    See app/services/batch_process.py for the folder layout, the per-tag
    "AI Extraction" export and the consolidated workbook this also produces.
    """
    try:
        found = scan_tag_folders()
    except BatchProcessError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from None
    if not found:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No tag folders with images were found to process.",
        )

    reference = f"BP-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(3).upper()}"
    grouped: OrderedDict[str, dict] = OrderedDict()
    for tag_number, description, files in found:
        grouped[tag_number] = {"description": description, "files": files}

    batch, _duplicates = await create_batch_with_items(
        db, reference, grouped, user, is_batch_process=True
    )
    background.add_task(run_batch_process, batch.id, user.id)

    return _batch_out(await _load_batch(db, batch.id, user))


@router.get("/by-status", response_model=Page[BatchOut])
async def list_batches_by_status(
    user: CurrentUser,
    db: DbSession,
    status_filter: str = Query(..., alias="status", pattern="^(completed|failed)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> Page[BatchOut]:
    """Backs the Home page's Completed/Failed Batch drill-down.

    "failed" also includes partial batches (some tags failed), matching the
    Home page's existing Failed Batches KPI definition.
    """
    statuses = (
        [BatchStatus.COMPLETED] if status_filter == "completed"
        else [BatchStatus.FAILED, BatchStatus.PARTIAL]
    )
    query = (
        select(Batch)
        .options(
            selectinload(Batch.items).selectinload(BatchItem.images),
            selectinload(Batch.items).selectinload(BatchItem.asset_tag),
        )
        .where(Batch.status.in_(statuses))
        .order_by(Batch.created_at.desc())
    )
    count_query = select(func.count()).select_from(Batch).where(Batch.status.in_(statuses))

    if user.role != UserRole.ADMIN:
        query = query.where(Batch.user_id == user.id)
        count_query = count_query.where(Batch.user_id == user.id)

    total = await db.scalar(count_query) or 0
    rows = (
        await db.scalars(query.offset((page - 1) * page_size).limit(page_size))
    ).all()
    return Page[BatchOut](
        items=[_batch_out(b) for b in rows], total=total, page=page, page_size=page_size
    )



@router.get("/images/extracted", response_model=Page[ExtractedImageOut])
async def list_extracted_images(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> Page[ExtractedImageOut]:
    """Backs the Home page's Total Images Extracted drill-down.

    Every uploaded image, newest first, with its parent tag's current status —
    an image doesn't carry its own status, only the tag (BatchItem) it belongs
    to does.
    """
    query = (
        select(TagImage, BatchItem.tag_number, BatchItem.status, Batch.reference)
        .join(BatchItem, BatchItem.id == TagImage.item_id)
        .join(Batch, Batch.id == BatchItem.batch_id)
        .order_by(TagImage.created_at.desc())
    )
    count_query = (
        select(func.count())
        .select_from(TagImage)
        .join(BatchItem, BatchItem.id == TagImage.item_id)
        .join(Batch, Batch.id == BatchItem.batch_id)
    )
    if user.role != UserRole.ADMIN:
        query = query.where(Batch.user_id == user.id)
        count_query = count_query.where(Batch.user_id == user.id)

    total = await db.scalar(count_query) or 0
    rows = (
        await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    ).all()
    items = [
        ExtractedImageOut(
            id=image.id,
            original_filename=image.original_filename,
            tag_number=tag_number,
            batch_reference=reference,
            status=item_status,
            created_at=image.created_at,
        )
        for image, tag_number, item_status, reference in rows
    ]
    return Page[ExtractedImageOut](items=items, total=total, page=page, page_size=page_size)


@router.get("/{batch_id}", response_model=BatchOut)
async def get_batch(batch_id: int, user: CurrentUser, db: DbSession) -> BatchOut:
    """Polled by the UI while the status rail advances."""
    return _batch_out(await _load_batch(db, batch_id, user))


@router.post("/{batch_id}/items/{item_id}/retry", response_model=BatchItemOut)
async def retry_item(
    batch_id: int, item_id: int, user: CurrentUser, db: DbSession, background: BackgroundTasks
) -> BatchItemOut:
    """Re-extract one failed tag in place — no new batch, tag, or image rows.

    Same "Re-Extract" button either way, but a Batch Process batch also needs
    its AI Extraction copy and consolidated workbook refreshed once the retry
    lands — see app/services/batch_process.py.
    """
    batch = await _load_batch(db, batch_id, user)
    item = next((i for i in batch.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That tag isn't part of this batch.")
    if item.status != ItemStatus.FAILED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only a failed tag can be retried.")

    item.status = ItemStatus.UPLOADED
    batch.status = BatchStatus.PROCESSING
    await db.commit()

    if batch.is_batch_process:
        background.add_task(reextract_batch_process_item, item.id, batch.id, user.id)
    else:
        background.add_task(reextract_item, item.id, batch.id, user.id)
    return _item_out(item)


async def _serve_image(image: TagImage) -> FileResponse:
    try:
        path = resolve_stored(image.stored_path)
    except FileNotFoundError:
        # Common for a tag synced in before app/services/sync_client.py
        # downloaded photo files (or from a page pulled before that existed):
        # the row replicated, the file on disk never did. Fetch it from
        # production now, on demand.
        path = await fetch_missing_photo(image.id, image.stored_path)
        if path is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "The photo file is missing from storage."
            ) from None
    except ValueError:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "The photo file is missing from storage."
        ) from None

    return FileResponse(path=path, filename=image.original_filename, media_type=image.media_type)


@router.get("/{batch_id}/images/{image_id}")
async def get_batch_image(
    batch_id: int, image_id: int, user: CurrentUser, db: DbSession
) -> FileResponse:
    """Serve one of the raw input photos this batch was uploaded with.

    Authorized for the batch's uploader OR the tag's extractor
    (AssetTag.created_by_id), not just the batch uploader alone. History and
    Search resolve "View Photo" through whichever batch item is *currently*
    the completed one for that tag_number (see BATCH_LOOKUP_ACTIONS in
    app/api/v1/history.py and search_tags in app/api/v1/tags.py) — if that
    shifts to a different batch after the fact (a re-extraction, an admin
    reprocessing it), a batch-ownership-only check 403s the very user who
    extracted the tag, even though it's plainly theirs. Admin is unaffected
    either way, which is why this only ever showed up for non-admins.
    """
    row = (
        await db.execute(
            select(TagImage, Batch.user_id, AssetTag.created_by_id)
            .join(BatchItem, BatchItem.id == TagImage.item_id)
            .join(Batch, Batch.id == BatchItem.batch_id)
            .outerjoin(AssetTag, AssetTag.id == BatchItem.asset_tag_id)
            .where(TagImage.id == image_id, BatchItem.batch_id == batch_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That photo isn't part of this batch.")
    image, batch_owner_id, tag_creator_id = row

    if user.role != UserRole.ADMIN and user.id not in (batch_owner_id, tag_creator_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "That photo belongs to another user's tag."
        )

    return await _serve_image(image)


def _photo_gallery_html(tag_number: str, token: str, count: int) -> str:
    """Simple unstyled gallery so a multi-photo tag's single INPUT PHOTO
    hyperlink can still reach every photo — one click each, same signed
    token, just a different `index`.
    """
    safe_tag = html.escape(tag_number)
    safe_token = quote(token)
    thumbs = "".join(
        f'<a href="/api/v1/batches/images/photo-link?token={safe_token}&index={i}" target="_blank">'
        f'<img src="/api/v1/batches/images/photo-link?token={safe_token}&index={i}" alt="Photo {i + 1}"></a>'
        for i in range(count)
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{safe_tag} photos</title>
<style>
body {{ font-family: Arial, sans-serif; background:#f5f6f8; margin:0; padding:24px; }}
h1 {{ font-size:16px; margin:0 0 16px; }}
.grid {{ display:flex; flex-wrap:wrap; gap:16px; }}
.grid img {{ max-width:280px; max-height:280px; border:1px solid #ccc; border-radius:4px; object-fit:cover; }}
</style></head>
<body><h1>{safe_tag} — {count} input photos</h1><div class="grid">{thumbs}</div></body></html>"""


@router.get("/images/photo-link")
async def get_photo_by_link(
    token: str, db: DbSession, index: int | None = Query(None, ge=0)
) -> Response:
    """Unauthenticated counterpart to `get_batch_image`, for the INPUT PHOTO
    hyperlink embedded in an exported Template workbook — see
    app.services.download_links. Guarded by a signed, expiring, tag-scoped
    token instead of CurrentUser.

    A tag with exactly one photo behaves exactly as before — the link opens
    that photo directly. A tag with several photos (the INPUT PHOTO column is
    always a single link, one per row) instead opens a small gallery page
    linking to each one via `&index=N`, so none of them are hidden behind
    "just the first photo" any more.
    """
    tag_number = verify_photo_token(token)
    if tag_number is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "This photo link is invalid or has expired."
        )
    images = (
        await db.scalars(
            select(TagImage)
            .join(BatchItem, BatchItem.id == TagImage.item_id)
            .where(BatchItem.tag_number == tag_number)
            .order_by(TagImage.id)
        )
    ).all()
    if not images:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No photo found for that tag.")

    if index is not None:
        if index >= len(images):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No photo at that position for this tag.")
        return await _serve_image(images[index])

    if len(images) == 1:
        return await _serve_image(images[0])

    return HTMLResponse(_photo_gallery_html(tag_number, token, len(images)))


@router.get("", response_model=list[BatchOut])
async def list_batches(user: CurrentUser, db: DbSession, limit: int = 20) -> list[BatchOut]:
    query = (
        select(Batch)
        .options(
            selectinload(Batch.items).selectinload(BatchItem.images),
            selectinload(Batch.items).selectinload(BatchItem.asset_tag),
        )
        .order_by(Batch.created_at.desc())
        .limit(min(limit, 100))
    )
    if user.role != UserRole.ADMIN:
        query = query.where(Batch.user_id == user.id)
    return [_batch_out(b) for b in (await db.scalars(query)).all()]
