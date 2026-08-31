"""Admin-only: user management and the Claude usage dashboard."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.config import settings
from app.core.deps import AdminUser, DbSession
from app.core.security import hash_password
from app.models import (
    Activity,
    ActivityAction,
    AssetTag,
    Batch,
    OrgCredits,
    User,
    UserRole,
)
from app.schemas.admin import (
    AdminStats,
    ClaudeModelUsage,
    ClaudeUsageDaily,
    ClaudeUsageSummary,
    OrgCreditsOut,
    OrgCreditsTopUp,
)
from app.schemas.auth import AdminPasswordReset, UserCreate, UserOut, UserUpdate
from app.schemas.common import Message
from app.services.anthropic_usage import (
    UNAVAILABLE_METRICS,
    ClaudeUsageUnavailable,
    fetch_claude_usage_report,
)
from app.services.org_credits import advance_usage_ledger
from app.services.sync_client import push_user

router = APIRouter(prefix="/admin", tags=["admin"])


# Users

@router.get("/users", response_model=list[UserOut])
async def list_users(admin: AdminUser, db: DbSession) -> list[UserOut]:
    rows = (await db.scalars(select(User).order_by(User.created_at.desc()))).all()
    return [UserOut.model_validate(u) for u in rows]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, admin: AdminUser, db: DbSession) -> UserOut:
    clash = await db.scalar(select(User).where(User.username == body.username))
    if clash is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"The username '{body.username}' is already taken."
        )
    user = User(
        username=body.username,
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()
    db.add(Activity(user_id=admin.id, action=ActivityAction.USER_CREATED,
                    detail=f"Created user {user.username} ({user.role.value})"))
    await db.commit()
    await db.refresh(user)
    # Best-effort, non-blocking: local user creation must succeed even if
    # production is unreachable. See sync_client.push_user.
    asyncio.create_task(push_user(user))
    return UserOut.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int, body: UserUpdate, admin: AdminUser, db: DbSession
) -> UserOut:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such user.")

    # Guard against an admin locking every administrator out of the system.
    if user.id == admin.id and (body.role == UserRole.USER or body.is_active is False):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "You can't remove your own admin access or disable your own account.",
        )

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    db.add(Activity(user_id=admin.id, action=ActivityAction.USER_UPDATED,
                    detail=f"Updated user {user.username}"))
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/users/{user_id}/reset-password", response_model=Message)
async def reset_password(
    user_id: int, body: AdminPasswordReset, admin: AdminUser, db: DbSession
) -> Message:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such user.")
    user.hashed_password = hash_password(body.new_password)
    db.add(Activity(user_id=admin.id, action=ActivityAction.PASSWORD_RESET,
                    detail=f"Reset password for {user.username}"))
    await db.commit()
    return Message(message=f"Password reset for {user.username}.")


@router.delete("/users/{user_id}", response_model=Message)
async def deactivate_user(user_id: int, admin: AdminUser, db: DbSession) -> Message:
    """Deactivate rather than delete — history rows must keep their author."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such user.")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "You can't disable your own account.")
    user.is_active = False
    db.add(Activity(user_id=admin.id, action=ActivityAction.USER_UPDATED,
                    detail=f"Disabled user {user.username}"))
    await db.commit()
    return Message(message=f"{user.username} has been disabled.")


# Claude usage dashboard — sourced entirely from Anthropic's official
# Usage & Cost Admin API. No local PostgreSQL usage records are read here.

@router.get("/usage", response_model=ClaudeUsageSummary)
async def usage(
    admin: AdminUser, days: int = Query(30, ge=1, le=31)
) -> ClaudeUsageSummary:
    """Claude token/cost usage as reported by Anthropic's Usage & Cost API.

    `days` is capped at 31 — that's the API's own maximum window at daily
    granularity. Returns `available=False` with a reason (never fabricated
    numbers) when the Admin API key is missing or the request fails.
    """
    now = datetime.now(timezone.utc)
    rate = settings.usd_to_inr_rate
    threshold = settings.claude_spend_warning_usd
    try:
        result = await fetch_claude_usage_report(days)
    except ClaudeUsageUnavailable as exc:
        return ClaudeUsageSummary(
            available=False, error=str(exc), generated_at=now, window_days=days,
            configured_model=settings.claude_model,
            input_tokens=0, output_tokens=0, total_tokens=0, total_cost_usd=0.0,
            total_cost_inr=0.0, usd_to_inr_rate=rate,
            by_model=[], daily=[], unavailable_metrics=UNAVAILABLE_METRICS,
            spend_warning_threshold_usd=threshold, spend_warning_triggered=False,
        )

    spent = round(result.total_cost_usd, 4)
    return ClaudeUsageSummary(
        available=True, error=None, generated_at=now, window_days=days,
        configured_model=settings.claude_model,
        input_tokens=result.total_input_tokens,
        output_tokens=result.total_output_tokens,
        total_tokens=result.total_input_tokens + result.total_output_tokens,
        total_cost_usd=spent,
        total_cost_inr=round(spent * rate, 2), usd_to_inr_rate=rate,
        by_model=[
            ClaudeModelUsage(
                model=m.model, input_tokens=m.input_tokens, output_tokens=m.output_tokens,
                total_tokens=m.input_tokens + m.output_tokens,
            )
            for m in result.by_model
        ],
        daily=[
            ClaudeUsageDaily(
                day=datetime.combine(d.day, datetime.min.time()),
                input_tokens=d.input_tokens, output_tokens=d.output_tokens,
                total_tokens=d.input_tokens + d.output_tokens,
                cost_usd=round(d.cost_usd, 6),
            )
            for d in result.daily
        ],
        unavailable_metrics=UNAVAILABLE_METRICS,
        spend_warning_threshold_usd=threshold, spend_warning_triggered=spent >= threshold,
    )


# Organization Credits — Estimated Balance = total purchased credits minus
# Anthropic's own reported usage. Anthropic's official API still has no
# endpoint for the account's actual balance, so an admin records what was
# purchased (as top-ups, never overwritten), and the app tracks Anthropic's
# real usage against it via services/org_credits.py. Never Anthropic's own
# balance figure — always labelled "Estimated" to the admin.

def _org_credits_out(
    row: OrgCredits | None, tracked_usage_usd: float = 0.0, usage_error: str | None = None
) -> OrgCreditsOut:
    rate = settings.usd_to_inr_rate
    if row is None:
        return OrgCreditsOut(
            total_purchased_usd=0.0, tracked_usage_usd=0.0,
            estimated_balance_usd=None, estimated_balance_inr=None,
            usd_to_inr_rate=rate, updated_at=None, usage_error=usage_error,
        )
    estimated = row.total_purchased_usd - tracked_usage_usd
    return OrgCreditsOut(
        total_purchased_usd=round(row.total_purchased_usd, 2),
        tracked_usage_usd=round(tracked_usage_usd, 2),
        estimated_balance_usd=round(estimated, 2),
        estimated_balance_inr=round(estimated * rate, 2),
        usd_to_inr_rate=rate,
        updated_at=row.updated_at,
        usage_error=usage_error,
    )


@router.get("/org-credits", response_model=OrgCreditsOut)
async def get_org_credits(admin: AdminUser, db: DbSession) -> OrgCreditsOut:
    row = await db.get(OrgCredits, 1)
    if row is None:
        return _org_credits_out(None)
    ledger = await advance_usage_ledger(row)
    await db.commit()
    await db.refresh(row)
    return _org_credits_out(row, ledger.tracked_usage_usd, ledger.usage_error)


@router.patch("/org-credits", response_model=OrgCreditsOut)
async def top_up_org_credits(
    body: OrgCreditsTopUp, admin: AdminUser, db: DbSession
) -> OrgCreditsOut:
    """Record a credit purchase — always adds to the running total.

    A brand-new row starts its usage ledger "through today", so a top-up
    only ever counts usage from the moment it's recorded onward — it never
    retroactively deducts spend that happened before this feature was set up.
    """
    row = await db.get(OrgCredits, 1)
    if row is None:
        row = OrgCredits(
            id=1, total_purchased_usd=body.top_up_usd, updated_by_user_id=admin.id,
            ledger_usage_usd=0.0, ledger_through_date=datetime.now(timezone.utc).date(),
        )
        db.add(row)
    else:
        row.total_purchased_usd += body.top_up_usd
        row.updated_by_user_id = admin.id
    ledger = await advance_usage_ledger(row)
    await db.commit()
    await db.refresh(row)
    return _org_credits_out(row, ledger.tracked_usage_usd, ledger.usage_error)


@router.get("/stats", response_model=AdminStats)
async def stats(admin: AdminUser, db: DbSession) -> AdminStats:
    async def count(model, *where):
        return int(await db.scalar(
            select(func.count()).select_from(model).where(*where) if where
            else select(func.count()).select_from(model)
        ) or 0)

    return AdminStats(
        total_users=await count(User),
        active_users=await count(User, User.is_active.is_(True)),
        total_tags=await count(AssetTag),
        total_batches=await count(Batch),
        total_uploads=await count(Activity, Activity.action == ActivityAction.UPLOAD),
        total_downloads=await count(Activity, Activity.action == ActivityAction.DOWNLOAD),
    )
