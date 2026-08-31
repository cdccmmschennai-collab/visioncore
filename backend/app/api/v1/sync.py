"""Read-only, token-authenticated endpoints the local Docker environment
polls to mirror completed extraction data.

Production never pushes and never learns whether a pull succeeded — these
routes just answer "what changed after this point", ordered by (updated_at,
id) so a caller can keep an exact resume position. See
app/services/sync_client.py for the puller that consumes this.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TypeVar

from fastapi import APIRouter, Query
from sqlalchemy import select, tuple_

from app.core.deps import DbSession, SyncAuth
from app.models import Activity, AssetTag, Batch, BatchItem, TagImage, User
from app.schemas.common import ORMModel
from app.schemas.sync import (
    SyncActivityOut,
    SyncAssetTagOut,
    SyncBatchItemOut,
    SyncBatchOut,
    SyncTagImageOut,
    SyncUserOut,
    SyncUserPush,
)

router = APIRouter(prefix="/sync", tags=["sync"])

#: Kept small and shared with sync_client.py — the client uses "did this page
#: come back full" as its signal that more rows are immediately pending.
PAGE_SIZE = 100

#: Same placeholder convention as sync_client._UNUSABLE_PASSWORD_HASH, for a
#: brand-new user arriving here via push_user() below — not a real bcrypt
#: hash, so it can never be logged into until an admin sets a real password
#: on this side.
_UNUSABLE_PASSWORD_HASH = "!sync-managed-account"

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

ModelT = TypeVar("ModelT")
SchemaT = TypeVar("SchemaT", bound=ORMModel)


async def _page(
    db: DbSession, model: type[ModelT], schema: type[SchemaT],
    since_updated_at: datetime, since_id: int,
) -> list[SchemaT]:
    rows = (
        await db.scalars(
            select(model)
            .where(tuple_(model.updated_at, model.id) > tuple_(since_updated_at, since_id))
            .order_by(model.updated_at, model.id)
            .limit(PAGE_SIZE)
        )
    ).all()
    return [schema.model_validate(r) for r in rows]


@router.get("/users", response_model=list[SyncUserOut])
async def sync_users(
    _: SyncAuth, db: DbSession,
    since_updated_at: datetime = Query(EPOCH), since_id: int = Query(0),
) -> list[SyncUserOut]:
    return await _page(db, User, SyncUserOut, since_updated_at, since_id)


@router.get("/asset-tags", response_model=list[SyncAssetTagOut])
async def sync_asset_tags(
    _: SyncAuth, db: DbSession,
    since_updated_at: datetime = Query(EPOCH), since_id: int = Query(0),
) -> list[SyncAssetTagOut]:
    return await _page(db, AssetTag, SyncAssetTagOut, since_updated_at, since_id)


@router.get("/batches", response_model=list[SyncBatchOut])
async def sync_batches(
    _: SyncAuth, db: DbSession,
    since_updated_at: datetime = Query(EPOCH), since_id: int = Query(0),
) -> list[SyncBatchOut]:
    return await _page(db, Batch, SyncBatchOut, since_updated_at, since_id)


@router.get("/batch-items", response_model=list[SyncBatchItemOut])
async def sync_batch_items(
    _: SyncAuth, db: DbSession,
    since_updated_at: datetime = Query(EPOCH), since_id: int = Query(0),
) -> list[SyncBatchItemOut]:
    return await _page(db, BatchItem, SyncBatchItemOut, since_updated_at, since_id)


@router.get("/tag-images", response_model=list[SyncTagImageOut])
async def sync_tag_images(
    _: SyncAuth, db: DbSession,
    since_updated_at: datetime = Query(EPOCH), since_id: int = Query(0),
) -> list[SyncTagImageOut]:
    return await _page(db, TagImage, SyncTagImageOut, since_updated_at, since_id)


@router.get("/activities", response_model=list[SyncActivityOut])
async def sync_activities(
    _: SyncAuth, db: DbSession,
    since_updated_at: datetime = Query(EPOCH), since_id: int = Query(0),
) -> list[SyncActivityOut]:
    return await _page(db, Activity, SyncActivityOut, since_updated_at, since_id)


@router.post("/users", response_model=SyncUserOut)
async def push_user(body: SyncUserPush, _: SyncAuth, db: DbSession) -> SyncUserOut:
    """Local -> production: receives a user pushed from app/services/
    sync_client.py::push_user after an admin creates it on the local Admin
    page. Upserted by username so a retried push is never duplicated.

    Never receives or sets a real password — a brand-new row here gets the
    same unusable placeholder hash a pulled-in user gets on the other side
    (see sync_client._UNUSABLE_PASSWORD_HASH); an admin sets a real password
    on this side separately. An existing account's password is left alone.
    """
    user = await db.scalar(select(User).where(User.username == body.username))
    if user is None:
        user = User(username=body.username, hashed_password=_UNUSABLE_PASSWORD_HASH)
        db.add(user)
    user.email = body.email
    user.full_name = body.full_name
    user.role = body.role
    user.is_active = body.is_active
    await db.commit()
    await db.refresh(user)
    return SyncUserOut.model_validate(user)
