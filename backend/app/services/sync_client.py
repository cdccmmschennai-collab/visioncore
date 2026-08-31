"""Pulls newly created/updated extraction data from a production VisionCore
instance into this environment's own PostgreSQL database.

Only runs when SYNC_SOURCE_URL is set — that is the local/mirror side.
Production leaves it blank, so it never starts this loop; it only serves
app/api/v1/sync.py to whoever authenticates against it.

Design:
  * One resource = one table, synced independently by its own (updated_at,
    id) cursor (persisted in SyncCursor). This — not a single cursor nested
    under batches — is what lets a later edit to an already-synced AssetTag
    (which doesn't touch its parent Batch row) still get picked up.
  * Resources are pulled in FK dependency order so a page's foreign keys
    always resolve locally before the row that references them arrives.
  * Idempotent upsert via `INSERT ... ON CONFLICT (id) DO UPDATE`, using
    production's own primary keys directly (safe because local is a pure
    mirror — see the ID-collision discussion this design followed from).
  * The cursor only advances after a page's rows are committed locally, so a
    crash mid-page is safely retried from the same page next cycle — the
    ON CONFLICT upsert makes that page idempotent, never duplicated.
  * A failure here never touches production: it's caught, logged, and
    retried on the next cycle. Production's extraction success is entirely
    independent of whether local sync is up.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.v1.sync import PAGE_SIZE
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models import Activity, AssetTag, Batch, BatchItem, SyncCursor, TagImage, User

logger = logging.getLogger(__name__)

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

#: (resource key, production URL path, model). Order is load-bearing: FK
#: parents before the children that reference them.
_RESOURCES: tuple[tuple[str, str, type], ...] = (
    ("users", "/api/v1/sync/users", User),
    ("asset_tags", "/api/v1/sync/asset-tags", AssetTag),
    ("batches", "/api/v1/sync/batches", Batch),
    ("batch_items", "/api/v1/sync/batch-items", BatchItem),
    ("tag_images", "/api/v1/sync/tag-images", TagImage),
    ("activities", "/api/v1/sync/activities", Activity),
)

#: Columns a sync upsert must never overwrite on a row that already exists
#: locally — safety fields, not data being mirrored.
_PROTECTED_COLUMNS: dict[type, frozenset[str]] = {
    User: frozenset({"hashed_password", "last_login_at"}),
}

#: Unusable bcrypt-shaped placeholder for a brand-new mirrored user — no
#: password will ever hash to this, so the account can't be logged into
#: locally until an admin sets a real password.
_UNUSABLE_PASSWORD_HASH = "!sync-managed-account"


def _coerce_row(table: sa.Table, row: dict[str, Any]) -> dict[str, Any]:
    """JSON gives back ISO datetime strings; DateTime columns need real
    datetimes for the asyncpg driver. Everything else (enums as their str
    value, JSONB as plain dict/list) is already the right shape.
    """
    values: dict[str, Any] = {}
    for col in table.columns:
        if col.name not in row:
            continue
        value = row[col.name]
        if value is not None and isinstance(col.type, sa.DateTime) and isinstance(value, str):
            value = datetime.fromisoformat(value)
        values[col.name] = value
    return values


async def _upsert_page(session, model: type, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    table = model.__table__
    protected = _PROTECTED_COLUMNS.get(model, frozenset())

    for row in rows:
        values = _coerce_row(table, row)
        if model is User and "hashed_password" not in row:
            values["hashed_password"] = _UNUSABLE_PASSWORD_HASH

        stmt = pg_insert(table).values(**values)
        update_cols = {
            c.name: getattr(stmt.excluded, c.name)
            for c in table.columns
            if c.name != "id" and c.name not in protected
        }
        stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_cols)
        await session.execute(stmt)


async def _cursor_for(session, resource: str) -> SyncCursor:
    cursor = await session.get(SyncCursor, resource)
    if cursor is None:
        cursor = SyncCursor(resource=resource, since_updated_at=EPOCH, since_id=0)
        session.add(cursor)
        await session.flush()
    return cursor


async def _sync_one_page(client: httpx.AsyncClient, resource: str, path: str, model: type) -> bool:
    """Pull and apply one page for one resource. Returns True if the page
    came back full (more rows immediately pending for this resource)."""
    async with AsyncSessionLocal() as session:
        cursor = await _cursor_for(session, resource)
        response = await client.get(
            path,
            params={
                "since_updated_at": cursor.since_updated_at.isoformat(),
                "since_id": cursor.since_id,
            },
        )
        response.raise_for_status()
        rows = response.json()
        if not rows:
            return False

        await _upsert_page(session, model, rows)

        last = rows[-1]
        cursor.since_updated_at = datetime.fromisoformat(last["updated_at"])
        cursor.since_id = last["id"]
        await session.commit()

        logger.info(
            "sync: %s +%d row(s), cursor now (updated_at=%s, id=%s)",
            resource, len(rows), cursor.since_updated_at.isoformat(), cursor.since_id,
        )
        return len(rows) == PAGE_SIZE


async def run_sync_loop() -> None:
    """Entry point wired into app.main's lifespan. Runs until cancelled."""
    if not settings.sync_source_url:
        return
    if not settings.sync_api_token:
        logger.warning(
            "SYNC_SOURCE_URL is set but SYNC_API_TOKEN is empty — sync will not start."
        )
        return

    headers = {"Authorization": f"Bearer {settings.sync_api_token}"}
    async with httpx.AsyncClient(
        base_url=settings.sync_source_url, headers=headers, timeout=30.0
    ) as client:
        logger.info("Production sync starting — pulling from %s", settings.sync_source_url)
        while True:
            try:
                more_pending = False
                for resource, path, model in _RESOURCES:
                    while await _sync_one_page(client, resource, path, model):
                        more_pending = True
                if not more_pending:
                    await asyncio.sleep(settings.sync_poll_interval_seconds)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Sync cycle failed — production data is unaffected; retrying in %ss",
                    settings.sync_poll_interval_seconds,
                )
                await asyncio.sleep(settings.sync_poll_interval_seconds)
