"""Admin-only: user management and the Claude usage dashboard."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.config import settings
from app.core.deps import AdminUser, AnyAdminUser, DbSession, team_scope
from app.core.security import hash_password
from app.models import (
    Activity,
    ActivityAction,
    ApiUsage,
    AssetTag,
    Batch,
    ClaudeApiConfig,
    OrgCredits,
    Team,
    User,
    UserRole,
)
from app.schemas.admin import (
    AdminStats,
    ClaudeConfigOut,
    ClaudeConfigTestResult,
    ClaudeConfigUpdate,
    ClaudeModelUsage,
    ClaudeUsageDaily,
    ClaudeUsageSummary,
    OrgCreditsOut,
    OrgCreditsTopUp,
    TeamUsageRow,
    TeamUsageSummary,
)
from app.schemas.auth import AdminPasswordReset, UserCreate, UserOut, UserUpdate
from app.schemas.common import Message
from app.services import claude_config as claude_config_service
from app.services.anthropic_usage import (
    UNAVAILABLE_METRICS,
    ClaudeUsageUnavailable,
    fetch_claude_usage_report,
)
from app.services.org_credits import advance_usage_ledger
from app.services.sync_client import push_user

router = APIRouter(prefix="/admin", tags=["admin"])


# Users — Overall Admin sees/manages every branch; a Branch Admin is scoped
# to exactly their own team, enforced here (query filters + explicit checks
# below), not just hidden in the frontend. See app/core/deps.py.

@router.get("/users", response_model=list[UserOut])
async def list_users(admin: AnyAdminUser, db: DbSession) -> list[UserOut]:
    query = select(User).order_by(User.created_at.desc())
    scope = team_scope(admin)
    if scope is not None:
        query = query.where(User.team == scope)
    rows = (await db.scalars(query)).all()
    return [UserOut.model_validate(u) for u in rows]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, admin: AnyAdminUser, db: DbSession) -> UserOut:
    if admin.role == UserRole.BRANCH_ADMIN:
        if body.role != UserRole.USER:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Branch admins can only create regular users."
            )
        if body.team != admin.team:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Branch admins can only create users in their own team ({admin.team.value}).",
            )
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
        team=body.team,
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


def _require_same_branch(admin: User, target: User) -> None:
    """A Branch Admin may only touch a user already in their own team — 403,
    not a silent no-op, so an ID-guessed request to another branch is
    rejected outright rather than quietly doing nothing."""
    if admin.role == UserRole.BRANCH_ADMIN and target.team != admin.team:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "That user belongs to another branch.")


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int, body: UserUpdate, admin: AnyAdminUser, db: DbSession
) -> UserOut:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such user.")
    _require_same_branch(admin, user)

    # Guard against an admin locking every administrator out of the system.
    if user.id == admin.id and (body.role == UserRole.USER or body.is_active is False):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "You can't remove your own admin access or disable your own account.",
        )

    if admin.role == UserRole.BRANCH_ADMIN:
        if body.role is not None and body.role != UserRole.USER:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Branch admins can't grant admin access."
            )
        if body.team is not None and body.team != admin.team:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Branch admins can't move a user to another branch."
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
    user_id: int, body: AdminPasswordReset, admin: AnyAdminUser, db: DbSession
) -> Message:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such user.")
    _require_same_branch(admin, user)
    user.hashed_password = hash_password(body.new_password)
    db.add(Activity(user_id=admin.id, action=ActivityAction.PASSWORD_RESET,
                    detail=f"Reset password for {user.username}"))
    await db.commit()
    return Message(message=f"Password reset for {user.username}.")


@router.delete("/users/{user_id}", response_model=Message)
async def deactivate_user(user_id: int, admin: AnyAdminUser, db: DbSession) -> Message:
    """Deactivate rather than delete — history rows must keep their author."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such user.")
    _require_same_branch(admin, user)
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "You can't disable your own account.")
    user.is_active = False
    db.add(Activity(user_id=admin.id, action=ActivityAction.USER_UPDATED,
                    detail=f"Disabled user {user.username}"))
    await db.commit()
    return Message(message=f"{user.username} has been disabled.")


# Claude API team configuration. A Branch Admin may view/update/test only
# their own team's key (never another branch's) — enforced below, same
# pattern as _require_same_branch for users. Keys are encrypted at rest (see
# app/services/claude_config.py); the plaintext key is only ever held in
# memory for the duration of a save/test-connection call, never returned to
# the frontend, logged, or included in an error message.

def _require_own_team(admin: User, team: Team) -> None:
    if admin.role == UserRole.BRANCH_ADMIN and team != admin.team:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Branch admins can only manage their own team's Claude API key."
        )


@router.get("/claude-configs", response_model=list[ClaudeConfigOut])
async def list_claude_configs(admin: AnyAdminUser, db: DbSession) -> list[ClaudeConfigOut]:
    scope = team_scope(admin)
    teams = [scope] if scope is not None else list(Team)
    rows = {c.team: c for c in (await db.scalars(select(ClaudeApiConfig))).all()}
    out: list[ClaudeConfigOut] = []
    for team in teams:
        row = rows.get(team)
        if row is None or not row.is_active:
            out.append(ClaudeConfigOut(team=team, masked_key=None, status="Not Configured", updated_at=None))
            continue
        masked = claude_config_service.mask_api_key(
            claude_config_service.decrypt_api_key(row.api_key_encrypted)
        )
        out.append(ClaudeConfigOut(team=team, masked_key=masked, status="Configured", updated_at=row.updated_at))
    return out


@router.put("/claude-configs/{team}", response_model=ClaudeConfigOut)
async def update_claude_config(
    team: Team, body: ClaudeConfigUpdate, admin: AnyAdminUser, db: DbSession
) -> ClaudeConfigOut:
    _require_own_team(admin, team)
    key = body.api_key.strip()
    if not key.startswith("sk-ant-"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "That doesn't look like a valid Claude API key."
        )
    config = await claude_config_service.set_api_key(db, team, key, admin.id)
    db.add(Activity(
        user_id=admin.id, action=ActivityAction.USER_UPDATED,
        detail=f"Updated the Claude API key for team {team.value}",
    ))
    await db.commit()
    await db.refresh(config)
    return ClaudeConfigOut(
        team=team, masked_key=claude_config_service.mask_api_key(key),
        status="Configured", updated_at=config.updated_at,
    )


@router.post("/claude-configs/{team}/test", response_model=ClaudeConfigTestResult)
async def test_claude_config(team: Team, admin: AnyAdminUser, db: DbSession) -> ClaudeConfigTestResult:
    """Tests the currently-saved key for `team` — a minimal Anthropic call
    (max_tokens=1), never logging or returning the key itself."""
    _require_own_team(admin, team)
    config = await claude_config_service.get_active_config(db, team)
    if config is None:
        return ClaudeConfigTestResult(success=False, message="Claude API is not configured for this team.")
    key = claude_config_service.decrypt_api_key(config.api_key_encrypted)
    success, message = await claude_config_service.test_connection(key)
    return ClaudeConfigTestResult(success=success, message=message)


@router.get("/usage/by-team", response_model=TeamUsageSummary)
async def usage_by_team(admin: AnyAdminUser, db: DbSession) -> TeamUsageSummary:
    """Team-level extraction usage from VisionCore's own api_usage table —
    distinct from GET /admin/usage below, which is Anthropic's org-wide
    official report and has no concept of team. Only successful extractions
    are counted (cost_usd/tokens are only populated on success — see
    pipeline.py), matching how the existing per-tag usage rows are recorded.
    A Branch Admin gets back only their own team's row — enforced by the
    WHERE clause below, not by filtering the response afterward.
    """
    scope = team_scope(admin)
    query = select(
        ApiUsage.team,
        func.count().label("extractions"),
        func.coalesce(func.sum(ApiUsage.input_tokens), 0).label("input_tokens"),
        func.coalesce(func.sum(ApiUsage.output_tokens), 0).label("output_tokens"),
        func.coalesce(func.sum(ApiUsage.cost_usd), 0.0).label("cost_usd"),
    ).where(ApiUsage.success.is_(True))
    if scope is not None:
        query = query.where(ApiUsage.team == scope)
    rows = (await db.execute(query.group_by(ApiUsage.team))).all()
    by_team = {r.team: r for r in rows}
    teams = [scope] if scope is not None else list(Team)
    return TeamUsageSummary(teams=[
        TeamUsageRow(
            team=team,
            extractions=by_team[team].extractions if team in by_team else 0,
            input_tokens=by_team[team].input_tokens if team in by_team else 0,
            output_tokens=by_team[team].output_tokens if team in by_team else 0,
            total_tokens=(
                (by_team[team].input_tokens + by_team[team].output_tokens) if team in by_team else 0
            ),
            cost_usd=round(float(by_team[team].cost_usd), 6) if team in by_team else 0.0,
        )
        for team in teams
    ])


# Claude usage dashboard — sourced entirely from Anthropic's official
# Usage & Cost Admin API. No local PostgreSQL usage records are read here.
# Overall Admin only: this is one org-wide report against a single Admin API
# key, with no per-team breakdown Anthropic's API can provide — GET
# /admin/usage/by-team above is the team-scoped equivalent branch admins use.

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
# balance figure — always labelled "Estimated" to the admin. Overall Admin
# only: one whole-org balance, no per-team breakdown exists or is meaningful.

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
async def stats(admin: AnyAdminUser, db: DbSession) -> AdminStats:
    scope = team_scope(admin)

    async def count(model, *where):
        return int(await db.scalar(
            select(func.count()).select_from(model).where(*where) if where
            else select(func.count()).select_from(model)
        ) or 0)

    if scope is None:
        total_tags = await count(AssetTag)
        total_uploads = await count(Activity, Activity.action == ActivityAction.UPLOAD)
        total_downloads = await count(Activity, Activity.action == ActivityAction.DOWNLOAD)
    else:
        # AssetTag/Activity carry no direct team column (AssetTag can be
        # shared across teams by design — see app/models/tag.py; Activity is
        # keyed by user_id only) — join through the owning user's team
        # instead, same attribution history.py/pipeline.py already use.
        total_tags = int(await db.scalar(
            select(func.count()).select_from(AssetTag)
            .join(User, User.id == AssetTag.created_by_id)
            .where(User.team == scope)
        ) or 0)
        total_uploads = int(await db.scalar(
            select(func.count()).select_from(Activity)
            .join(User, User.id == Activity.user_id)
            .where(Activity.action == ActivityAction.UPLOAD, User.team == scope)
        ) or 0)
        total_downloads = int(await db.scalar(
            select(func.count()).select_from(Activity)
            .join(User, User.id == Activity.user_id)
            .where(Activity.action == ActivityAction.DOWNLOAD, User.team == scope)
        ) or 0)

    user_where = () if scope is None else (User.team == scope,)
    batch_where = () if scope is None else (Batch.team == scope,)
    return AdminStats(
        total_users=await count(User, *user_where),
        active_users=await count(User, User.is_active.is_(True), *user_where),
        total_tags=total_tags,
        total_batches=await count(Batch, *batch_where),
        total_uploads=total_uploads,
        total_downloads=total_downloads,
    )
