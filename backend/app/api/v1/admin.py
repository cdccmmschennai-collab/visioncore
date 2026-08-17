"""Admin-only: user management and the Claude usage dashboard."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import Date, Integer, cast, func, select

from app.core.config import settings
from app.core.deps import AdminUser, DbSession
from app.core.security import hash_password
from app.models import (
    Activity,
    ActivityAction,
    ApiUsage,
    AssetTag,
    Batch,
    User,
    UserRole,
)
from app.schemas.admin import AdminStats, UsageDaily, UsageSummary
from app.schemas.auth import AdminPasswordReset, UserCreate, UserOut, UserUpdate
from app.schemas.common import Message

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


# Usage dashboard 

@router.get("/usage", response_model=UsageSummary)
async def usage(
    admin: AdminUser, db: DbSession, days: int = Query(30, ge=1, le=365)
) -> UsageSummary:
    """Token and spend totals measured from recorded API calls.

    Anthropic exposes no balance endpoint, so this is spend *measured* from each
    response's usage block and priced with the configured rates — not a figure
    read back from the account.
    """
    totals = (await db.execute(
        select(
            func.count(ApiUsage.id),
            func.coalesce(func.sum(ApiUsage.input_tokens), 0),
            func.coalesce(func.sum(ApiUsage.output_tokens), 0),
            func.coalesce(func.sum(ApiUsage.cost_usd), 0.0),
            func.coalesce(func.avg(ApiUsage.latency_ms), 0),
            func.coalesce(func.sum(cast(ApiUsage.success, Integer)), 0),
        )
    )).one()
    calls, in_tokens, out_tokens, cost, avg_latency, successes = totals

    since = datetime.now(timezone.utc) - timedelta(days=days)
    daily_rows = (await db.execute(
        select(
            cast(ApiUsage.created_at, Date).label("day"),
            func.coalesce(func.sum(ApiUsage.input_tokens), 0),
            func.coalesce(func.sum(ApiUsage.output_tokens), 0),
            func.coalesce(func.sum(ApiUsage.cost_usd), 0.0),
            func.count(ApiUsage.id),
        )
        .where(ApiUsage.created_at >= since)
        .group_by(cast(ApiUsage.created_at, Date))
        .order_by(cast(ApiUsage.created_at, Date))
    )).all()

    budget = settings.claude_credit_budget_usd
    spent = float(cost or 0.0)

    return UsageSummary(
        model=settings.claude_model,
        total_calls=int(calls or 0),
        successful_calls=int(successes or 0),
        failed_calls=int((calls or 0) - (successes or 0)),
        input_tokens=int(in_tokens or 0),
        output_tokens=int(out_tokens or 0),
        total_tokens=int((in_tokens or 0) + (out_tokens or 0)),
        total_cost_usd=round(spent, 4),
        credit_budget_usd=budget,
        remaining_usd=round(max(0.0, budget - spent), 4),
        percent_used=round(min(100.0, (spent / budget * 100) if budget else 0.0), 2),
        avg_latency_ms=int(avg_latency or 0),
        input_price_per_mtok=settings.claude_input_price_per_mtok,
        output_price_per_mtok=settings.claude_output_price_per_mtok,
        daily=[
            UsageDaily(
                day=datetime.combine(day, datetime.min.time()),
                input_tokens=int(i), output_tokens=int(o),
                cost_usd=round(float(c), 6), calls=int(n),
            )
            for day, i, o, c, n in daily_rows
        ],
    )


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
