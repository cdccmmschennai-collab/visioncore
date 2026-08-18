"""The extraction pipeline: uploaded -> extracting -> processing -> completed.

Runs as a FastAPI background task. Each tag gets its own database session and
its own try/except, so one tag failing (an unreadable photo, a rate limit)
leaves the rest of the batch to finish rather than taking the batch down.

At this scale — ten tags per batch, one vision call each — background tasks are
the right tool. Move to Celery or ARQ when you need retries that survive an API
restart, or a worker pool separate from the web process.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models import (
    Activity,
    ActivityAction,
    ApiUsage,
    AssetTag,
    Batch,
    BatchItem,
    BatchStatus,
    ItemStatus,
)
from app.services.ai_extractor import get_extractor
from app.services.claude_extractor import ExtractionError
from app.services.excel_ai import build_ai_workbook
from app.services.excel_template import build_template_workbook
from app.services.filename_parser import excel_basename
from app.services.storage import (
    ai_output_name,
    template_output_name,
    write_export,
)

logger = logging.getLogger(__name__)


def template_path_columns(tag_number: str, description: str, photo_names: list[str]) -> tuple[str, str]:
    """Build the INPUT PHOTOS / OUTPUT WITH IMAGES cells for the Template sheet."""
    stem = excel_basename(tag_number, description)
    in_prefix = settings.template_input_path_prefix.rstrip("\\/")
    out_prefix = settings.template_output_path_prefix.rstrip("\\/")
    photo = photo_names[0] if photo_names else f"{stem}.jpg"

    input_cell = f"{in_prefix}\\{photo}" if in_prefix else photo
    if len(photo_names) > 1:
        extra = ", ".join(photo_names[1:])
        input_cell = f"{input_cell}; {extra}"
    output_cell = f"{out_prefix}\\{stem}.xlsx" if out_prefix else f"{stem}.xlsx"
    return input_cell, output_cell


async def generate_workbooks(
    session: AsyncSession,
    asset_tag: AssetTag,
    photo_names: list[str],
) -> tuple[str, str]:
    """Write both workbooks to disk and record their paths on the AssetTag."""
    stem = excel_basename(asset_tag.tag_number, asset_tag.description)
    input_cell, output_cell = template_path_columns(
        asset_tag.tag_number, asset_tag.description, photo_names
    )

    ai_bytes = build_ai_workbook(
        asset_tag.ai_payload, asset_tag.tag_number, asset_tag.description, photo_names
    )
    template_bytes = build_template_workbook([{
        "payload": asset_tag.final_payload,
        "ai_payload": asset_tag.ai_payload,
        "input_photos": input_cell,
        "output_file": output_cell,
    }])

    ai_path = write_export(asset_tag.tag_number, ai_output_name(stem), ai_bytes)
    template_path = write_export(asset_tag.tag_number, template_output_name(stem), template_bytes)

    asset_tag.ai_excel_path = str(ai_path)
    asset_tag.template_excel_path = str(template_path)
    await session.flush()
    return str(ai_path), str(template_path)


async def _set_status(session: AsyncSession, item: BatchItem, status: ItemStatus,
                      error: str | None = None) -> None:
    item.status = status
    item.error_message = error
    await session.commit()


async def process_item(item_id: int, user_id: int) -> None:
    """Extract, persist and export a single tag. Never raises to the caller."""
    async with AsyncSessionLocal() as session:
        item = await session.scalar(
            select(BatchItem)
            .options(selectinload(BatchItem.images), selectinload(BatchItem.batch))
            .where(BatchItem.id == item_id)
        )
        if item is None:
            logger.warning("process_item: batch item %s vanished", item_id)
            return

        # A tag can be claimed by a concurrent batch between upload and
        # processing, so re-check rather than trusting the upload-time check.
        existing = await session.scalar(
            select(AssetTag).where(AssetTag.tag_number == item.tag_number)
        )
        if existing is not None:
            item.asset_tag_id = existing.id
            await _set_status(session, item, ItemStatus.DUPLICATE)
            session.add(Activity(
                user_id=user_id,
                action=ActivityAction.DUPLICATE_BLOCKED,
                tag_number=item.tag_number,
                description=item.description,
                detail="Tag already extracted \u2014 existing record returned",
            ))
            await session.commit()
            return

        photo_names = [img.original_filename for img in item.images]
        photo_paths = [img.stored_path for img in item.images]

        await _set_status(session, item, ItemStatus.EXTRACTING)

        try:
            extractor = get_extractor()
            result = await extractor.extract(photo_paths, item.tag_number, item.description)
        except ExtractionError as exc:
            logger.exception("Extraction failed for %s", item.tag_number)
            session.add(ApiUsage(
                user_id=user_id, tag_number=item.tag_number, model=settings.claude_model,
                success=False, error_message=str(exc)[:2000],
            ))
            await _set_status(session, item, ItemStatus.FAILED, str(exc))
            return
        except Exception as exc:                      # noqa: BLE001 - last resort
            logger.exception("Unexpected extraction error for %s", item.tag_number)
            await _set_status(session, item, ItemStatus.FAILED, f"Unexpected error: {exc}")
            return

        session.add(ApiUsage(
            user_id=user_id, tag_number=item.tag_number, model=result.model,
            input_tokens=result.input_tokens, output_tokens=result.output_tokens,
            cost_usd=result.cost_usd, latency_ms=result.latency_ms, success=True,
        ))
        await session.commit()

        await _set_status(session, item, ItemStatus.PROCESSING)

        # final_payload starts as a copy of the AI's answer; edits diverge it.
        asset_tag = AssetTag(
            tag_number=item.tag_number,
            description=item.description,
            ai_payload=result.payload,
            final_payload=result.payload,
            created_by_id=user_id,
        )
        session.add(asset_tag)
        try:
            await session.flush()
        except IntegrityError:
            # Lost the race against a concurrent batch; report, don't fail.
            await session.rollback()
            existing = await session.scalar(
                select(AssetTag).where(AssetTag.tag_number == item.tag_number)
            )
            if existing:
                item.asset_tag_id = existing.id
            await _set_status(session, item, ItemStatus.DUPLICATE)
            return

        try:
            await generate_workbooks(session, asset_tag, photo_names)
        except Exception as exc:                      # noqa: BLE001
            logger.exception("Workbook generation failed for %s", item.tag_number)
            await session.rollback()
            await _set_status(session, item, ItemStatus.FAILED, f"Excel generation failed: {exc}")
            return

        item.asset_tag_id = asset_tag.id
        item.status = ItemStatus.COMPLETED
        item.error_message = None
        session.add(Activity(
            user_id=user_id, action=ActivityAction.EXTRACT,
            tag_number=item.tag_number, description=item.description,
            detail=f"Extracted from {len(photo_paths)} photo(s)",
            meta={"input_tokens": result.input_tokens,
                  "output_tokens": result.output_tokens,
                  "cost_usd": round(result.cost_usd, 6)},
        ))
        await session.commit()


async def process_batch(batch_id: int, user_id: int) -> None:
    """Run every pending tag in a batch, then roll the batch status up."""
    async with AsyncSessionLocal() as session:
        batch = await session.scalar(
            select(Batch).options(selectinload(Batch.items)).where(Batch.id == batch_id)
        )
        if batch is None:
            return
        batch.status = BatchStatus.PROCESSING
        item_ids = [i.id for i in batch.items if i.status == ItemStatus.UPLOADED]
        await session.commit()

    for item_id in item_ids:
        await process_item(item_id, user_id)

    async with AsyncSessionLocal() as session:
        batch = await session.scalar(
            select(Batch).options(selectinload(Batch.items)).where(Batch.id == batch_id)
        )
        if batch is None:
            return
        statuses = {i.status for i in batch.items}
        if ItemStatus.FAILED not in statuses:
            batch.status = BatchStatus.COMPLETED
        elif statuses <= {ItemStatus.FAILED}:
            batch.status = BatchStatus.FAILED
        else:
            batch.status = BatchStatus.PARTIAL
        await session.commit()
