"""Shared FastAPI dependencies: current user, role gates, pagination."""
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models import Team, User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)
sync_bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sign in again to continue.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None:
        raise CREDENTIALS_ERROR
    claims = decode_token(credentials.credentials, expected_type="access")
    if claims is None:
        raise CREDENTIALS_ERROR

    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError):
        raise CREDENTIALS_ERROR from None

    user = await db.get(User, user_id)
    if user is None:
        raise CREDENTIALS_ERROR
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled. Contact an administrator.",
        )
    return user


async def require_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Overall Admin only — unchanged meaning. Used for org-wide operations
    a Branch Admin must never reach: Claude API key configuration, the
    Anthropic-official usage report, organization credits, and role/branch
    promotion. See require_any_admin below for the broader, team-scoped gate."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This area is restricted to administrators.",
        )
    return user


async def require_any_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Overall Admin OR Branch Admin. The endpoint itself is responsible for
    scoping its query to `team_scope(user)` — this only gates entry."""
    if user.role not in (UserRole.ADMIN, UserRole.BRANCH_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This area is restricted to administrators.",
        )
    return user


def team_scope(user: User) -> Team | None:
    """None = unrestricted (Overall Admin sees every branch). A Team value =
    restricted to that branch only (Branch Admin). Never meaningful for a
    plain USER — those endpoints stay scoped to their own user_id instead,
    independent of team."""
    return user.team if user.role == UserRole.BRANCH_ADMIN else None


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
AnyAdminUser = Annotated[User, Depends(require_any_admin)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def require_sync_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(sync_bearer_scheme)],
) -> None:
    """Gate for app/api/v1/sync.py — a shared-secret token, not a user login.

    Fails closed: if SYNC_API_TOKEN isn't configured, the endpoints are
    unreachable rather than accepting an empty/blank token as valid.
    """
    if not settings.sync_api_token:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Sync is not configured on this server."
        )
    if credentials is None or not secrets.compare_digest(
        credentials.credentials, settings.sync_api_token
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Invalid sync token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


SyncAuth = Annotated[None, Depends(require_sync_token)]
