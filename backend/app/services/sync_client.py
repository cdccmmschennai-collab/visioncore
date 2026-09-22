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
    mirror for every resource except users — see _CONFLICT_COLUMN and
    _user_id_map below for why users needs different handling, and the
    ID-collision discussion this design originally followed from).
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
from pathlib import Path
from typing import Any

import httpx
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.v1.sync import PAGE_SIZE
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models import Activity, AssetTag, Batch, BatchItem, SyncCursor, TagImage, User
from app.services.storage import local_path_for

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

#: ON CONFLICT arbiter column per resource. Defaults to "id" — safe only
#: when local is a genuinely pure mirror, i.e. rows of that resource are
#: ever created by pulling from production, never independently on this
#: side (true for every resource except users). Overridden to "username"
#: for User: push_user (both directions — see below and app/api/v1/
#: sync.py) means a user CAN be created independently on either side, each
#: auto-assigning its own id from its own sequence, so the same real-world
#: account can end up under two different ids across environments.
#: username — the actual business key an admin chose — is what correctly
#: identifies "the same user" here; upserting by id instead would either
#: create a duplicate-username row or collide with uq_users_username.
_CONFLICT_COLUMN: dict[type, str] = {User: "username"}

#: Every other synced resource's own id is a pure mirror of production's —
#: safe to use as-is. But a column on one of THEM that references users.id
#: is not: because a user can now be created independently on both sides
#: (see _CONFLICT_COLUMN above), the SAME account can sit under two
#: different ids across environments, so a raw production user_id pulled in
#: on an activities/batches/asset_tags row may not exist locally at all —
#: it needs translating through _user_id_map first. Resource -> the column
#: names on it that hold a users.id reference.
_USER_FK_COLUMNS: dict[type, tuple[str, ...]] = {
    AssetTag: ("created_by_id", "edited_by_id"),
    Batch: ("user_id",),
    Activity: ("user_id",),
}

#: production user id -> this mirror's own local id for that same user
#: (matched by username, populated in _upsert_page as `users` pages sync —
#: see _RESOURCES' FK ordering, which guarantees users syncs before anything
#: that could need this). Process-lifetime cache: once learned, a mapping
#: stays valid — usernames aren't renamed, and a user is never re-created
#: under a new id on either side.
_user_id_map: dict[int, int] = {}

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


def _updatable_columns(values: dict[str, Any], protected: frozenset[str]) -> list[str]:
    """Which columns an upsert's ON CONFLICT DO UPDATE should touch: only
    ones `values` actually carries, minus `id` and any protected column.

    Deliberately NOT "every column the table has" — a column the sender's
    Sync*Out schema doesn't include (e.g. one added after that schema was
    last updated) is simply absent from `values`. If the SET clause included
    it anyway, `stmt.excluded.<col>` would resolve to that column's DEFAULT
    (it was never in the INSERT's value list), silently overwriting an
    existing row's real value with the schema default on every future
    upsert — exactly what happened to `users.team` before this existed.
    """
    return [name for name in values if name != "id" and name not in protected]


async def _upsert_page(session, model: type, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    table = model.__table__
    protected = _PROTECTED_COLUMNS.get(model, frozenset())
    conflict_col = _CONFLICT_COLUMN.get(model, "id")

    for row in rows:
        values = _coerce_row(table, row)
        if model is User and "hashed_password" not in row:
            values["hashed_password"] = _UNUSABLE_PASSWORD_HASH

        for fk_col in _USER_FK_COLUMNS.get(model, ()):
            if fk_col in values and values[fk_col] is not None:
                values[fk_col] = _user_id_map.get(values[fk_col], values[fk_col])

        stmt = pg_insert(table).values(**values)
        update_cols = {
            name: getattr(stmt.excluded, name)
            for name in _updatable_columns(values, protected)
            if name != conflict_col
        }
        stmt = stmt.on_conflict_do_update(index_elements=[conflict_col], set_=update_cols)
        await session.execute(stmt)

        if model is User:
            local_id = await session.scalar(sa.select(User.id).where(User.username == values["username"]))
            if local_id is not None:
                _user_id_map[row["id"]] = local_id


async def _bump_sequence(session, model: type) -> None:
    """Upserting production's own explicit `id` values never advances this
    table's local serial sequence — so a later local-only insert into the
    same table (e.g. a login Activity row) can collide with an id a sync
    page just claimed. Move the sequence past the current max after every
    upsert so local inserts never reuse one.
    """
    table = model.__table__
    max_id = await session.scalar(sa.select(sa.func.max(table.c.id)))
    if max_id is None:
        return
    await session.execute(
        sa.text("SELECT setval(pg_get_serial_sequence(:table, 'id'), :max_id)"),
        {"table": table.name, "max_id": max_id},
    )


async def _sync_photo_files(client: httpx.AsyncClient, rows: list[dict[str, Any]]) -> None:
    """A tag_images row only carries a path string — the actual file was
    never part of it (see app/api/v1/sync.py::sync_tag_images). Download the
    real bytes for any row this page just referenced that isn't already on
    disk here, so "View Photo" works for a synced-in tag too. Naturally
    idempotent: a row whose file already exists (a re-synced duplicate, or a
    previous cycle that already fetched it) is simply skipped.
    """
    for row in rows:
        target = local_path_for(row["stored_path"])
        if target.is_file():
            continue
        try:
            response = await client.get(f"/api/v1/sync/tag-images/{row['id']}/file")
            response.raise_for_status()
        except Exception:
            logger.exception("Could not fetch photo file for tag_image %s", row["id"])
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)


async def fetch_missing_photo(image_id: int, stored_path: str) -> Path | None:
    """On-demand fallback for a tag_images row whose file isn't on disk here —
    used by app/api/v1/batches.py::get_batch_image when resolve_stored 404s.
    Covers rows pulled in by a page that ran before _sync_photo_files existed
    (their sync cursor has already moved past them, so the pull loop above
    will never revisit them). No-op on production itself (sync_source_url
    unset), same guard as run_sync_loop.
    """
    if not settings.sync_source_url or not settings.sync_api_token:
        return None
    headers = {"Authorization": f"Bearer {settings.sync_api_token}"}
    try:
        async with httpx.AsyncClient(
            base_url=settings.sync_source_url, headers=headers, timeout=30.0
        ) as client:
            response = await client.get(f"/api/v1/sync/tag-images/{image_id}/file")
            response.raise_for_status()
    except Exception:
        logger.exception("Could not fetch photo file for tag_image %s", image_id)
        return None
    target = local_path_for(stored_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(response.content)
    return target


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

        # A page can contain a chain of tag_number edits/swaps across several
        # asset_tags rows (production allows renaming an existing tag).
        # Replaying it in id order can transiently collide with another row's
        # not-yet-updated value under an immediate check, even though the
        # page's final state is valid — so check deferrable constraints (see
        # uq_asset_tags_tag_number, migration 0008) at COMMIT instead.
        await session.execute(sa.text("SET CONSTRAINTS ALL DEFERRED"))
        await _upsert_page(session, model, rows)
        await _bump_sequence(session, model)
        if resource == "tag_images":
            await _sync_photo_files(client, rows)

        last = rows[-1]
        cursor.since_updated_at = datetime.fromisoformat(last["updated_at"])
        cursor.since_id = last["id"]
        await session.commit()

        logger.info(
            "sync: %s +%d row(s), cursor now (updated_at=%s, id=%s)",
            resource, len(rows), cursor.since_updated_at.isoformat(), cursor.since_id,
        )
        return len(rows) == PAGE_SIZE


async def _refresh_user_id_map(client: httpx.AsyncClient) -> None:
    """Full reconciliation of `_user_id_map` against production, independent
    of the persisted `users` SyncCursor. Run once at startup: `_user_id_map`
    is in-memory only (reset on every process restart), so without this, a
    page for any OTHER resource (asset_tags/batches/activities) referencing
    a user whose own `users` page was consumed in a PREVIOUS process
    lifetime — the `users` cursor is already past it, so no new page for it
    arrives this run — would have no mapping to resolve that reference
    against, even though the user genuinely exists locally under a
    different id (see _CONFLICT_COLUMN).
    """
    since_updated_at, since_id = EPOCH.isoformat(), 0
    while True:
        response = await client.get(
            "/api/v1/sync/users",
            params={"since_updated_at": since_updated_at, "since_id": since_id},
        )
        response.raise_for_status()
        rows = response.json()
        if not rows:
            return
        async with AsyncSessionLocal() as session:
            for row in rows:
                local_id = await session.scalar(
                    sa.select(User.id).where(User.username == row["username"])
                )
                if local_id is not None:
                    _user_id_map[row["id"]] = local_id
        last = rows[-1]
        since_updated_at, since_id = last["updated_at"], last["id"]
        if len(rows) < PAGE_SIZE:
            return


async def push_user(user: User) -> None:
    """Local -> production: best-effort push of a locally-created user so it
    also shows up on production — the inverse of the pull loop below, added
    only for User because that's the one thing an admin creates locally that
    also needs to exist on production. Called from
    app/api/v1/admin.py::create_user as a fire-and-forget background task,
    so local user creation always succeeds even if production is
    unreachable; any failure here is logged and never raised.

    Never sends a password — see app/api/v1/sync.py::push_user for how the
    production row is created instead.
    """
    if not settings.sync_source_url or not settings.sync_api_token:
        return
    headers = {"Authorization": f"Bearer {settings.sync_api_token}"}
    payload = {
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "team": user.team.value,
        "is_active": user.is_active,
    }
    try:
        async with httpx.AsyncClient(
            base_url=settings.sync_source_url, headers=headers, timeout=10.0
        ) as client:
            response = await client.post("/api/v1/sync/users", json=payload)
            response.raise_for_status()
        logger.info("Pushed user %s to production", user.username)
    except Exception:
        logger.exception(
            "Could not push user %s to production — it exists locally only "
            "until the next successful push", user.username,
        )


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
        try:
            await _refresh_user_id_map(client)
        except Exception:
            logger.exception(
                "Could not build the initial production->local user id map — "
                "FK references to a user with a mismatched id may fail until a "
                "later cycle retries this."
            )
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
