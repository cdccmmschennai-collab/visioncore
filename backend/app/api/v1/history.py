"""Upload and download history — scoped to the caller unless they're an admin."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query
from sqlalchemy import Integer, and_, cast, func, or_, select
from sqlalchemy.orm import aliased, selectinload

from app.core.deps import CurrentUser, DbSession
from app.models import Activity, ActivityAction, AssetTag, Batch, BatchItem, ItemStatus, User, UserRole
from app.schemas.common import Page
from app.schemas.tag import HistoryRow

router = APIRouter(prefix="/history", tags=["history"])

#: Actions worth surfacing on the History page. Logins are audited but are
#: noise in a data-migration log, so they are filtered out by default.
VISIBLE_ACTIONS = (
    ActivityAction.UPLOAD,
    ActivityAction.EXTRACT,
    ActivityAction.EDIT,
    ActivityAction.DOWNLOAD,
    ActivityAction.DUPLICATE_BLOCKED,
)

#: These actions operate on an already-extracted tag rather than a fresh
#: upload, so there's no batch_id on the activity itself — resolve one via
#: the batch item that originally completed this tag, so History can still
#: offer "View photos" for them.
BATCH_LOOKUP_ACTIONS = (ActivityAction.EXTRACT, ActivityAction.DOWNLOAD, ActivityAction.DUPLICATE_BLOCKED)

STATUS_LABEL = {
    ActivityAction.UPLOAD: "Uploaded",
    ActivityAction.EXTRACT: "Completed",
    ActivityAction.EDIT: "Saved",
    ActivityAction.DOWNLOAD: "Downloaded",
    ActivityAction.DUPLICATE_BLOCKED: "Duplicate",
}


@router.get("", response_model=Page[HistoryRow])
async def list_history(
    user: CurrentUser,
    db: DbSession,
    search: str = Query("", max_length=128),
    action: str = Query("", max_length=32),
    mine_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> Page[HistoryRow]:
    completed_item = aliased(BatchItem)
    # An Activity row has no foreign key to what it's about — only a
    # tag_number string (for tag actions) or a batch id tucked inside `meta`
    # (for UPLOAD) — precisely so the audit log used to survive that record
    # being deleted later. The production History page must NOT do that: a
    # row is only shown while the record it refers to still exists, so a
    # direct-SQL (or app) deletion disappears from History on next refresh.
    # upload_batch resolves UPLOAD's meta->>'batch_id' against a live Batch
    # row; every other visible action is required to still resolve to a
    # live AssetTag via the join below.
    upload_batch = aliased(Batch)
    upload_batch_id = cast(Activity.meta["batch_id"].astext, Integer)
    record_exists = or_(
        and_(Activity.action == ActivityAction.UPLOAD, upload_batch.id.is_not(None)),
        and_(Activity.action != ActivityAction.UPLOAD, AssetTag.id.is_not(None)),
    )

    query = (
        select(Activity, User.username, AssetTag.id,
               completed_item.batch_id, completed_item.id)
        .join(User, User.id == Activity.user_id, isouter=True)
        .join(AssetTag, AssetTag.tag_number == Activity.tag_number, isouter=True)
        .join(
            completed_item,
            and_(completed_item.asset_tag_id == AssetTag.id,
                 completed_item.status == ItemStatus.COMPLETED),
            isouter=True,
        )
        .join(upload_batch, upload_batch.id == upload_batch_id, isouter=True)
        .where(Activity.action.in_(VISIBLE_ACTIONS), record_exists)
    )
    count_query = (
        select(func.count())
        .select_from(Activity)
        .join(AssetTag, AssetTag.tag_number == Activity.tag_number, isouter=True)
        .join(upload_batch, upload_batch.id == upload_batch_id, isouter=True)
        .where(Activity.action.in_(VISIBLE_ACTIONS), record_exists)
    )

    # Non-admins only ever see their own rows, regardless of the flag.
    if user.role != UserRole.ADMIN or mine_only:
        query = query.where(Activity.user_id == user.id)
        count_query = count_query.where(Activity.user_id == user.id)

    if action.strip():
        query = query.where(Activity.action == action.strip())
        count_query = count_query.where(Activity.action == action.strip())

    if search.strip():
        pattern = f"%{search.strip()}%"
        condition = or_(
            Activity.tag_number.ilike(pattern),
            Activity.description.ilike(pattern),
            Activity.detail.ilike(pattern),
        )
        query = query.where(condition)
        count_query = count_query.where(condition)

    total = await db.scalar(count_query) or 0
    rows = (
        await db.execute(
            query.order_by(Activity.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    items = [
        HistoryRow(
            id=activity.id,
            date=activity.created_at,
            tag_number=activity.tag_number,
            description=activity.description,
            action=activity.action.value,
            status=STATUS_LABEL.get(activity.action, activity.action.value.title()),
            username=username,
            detail=activity.detail,
            asset_tag_id=asset_tag_id,
            can_download=asset_tag_id is not None,
            batch_id=(
                activity.meta.get("batch_id") if activity.action == ActivityAction.UPLOAD
                else completed_batch_id if activity.action in BATCH_LOOKUP_ACTIONS
                else None
            ),
            batch_item_id=(
                activity.meta.get("item_id") if activity.action == ActivityAction.UPLOAD
                else completed_item_id if activity.action in BATCH_LOOKUP_ACTIONS
                else None
            ),
        )
        for activity, username, asset_tag_id, completed_batch_id, completed_item_id in rows
    ]
    return Page[HistoryRow](items=items, total=total, page=page, page_size=page_size)
