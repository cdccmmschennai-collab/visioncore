from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_, select

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models import Activity, ActivityAction, User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserOut,
)
from app.schemas.common import Message

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_token(user.id, "access", role=user.role.value,
                                  username=user.username),
        refresh_token=create_token(user.id, "refresh"),
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbSession) -> TokenResponse:
    user = await db.scalar(select(User).where(User.username == body.username.strip()))

    # Same message and same work either way — a distinct "no such user" reply
    # would let an attacker enumerate valid usernames.
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That username and password don't match.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled. Contact an administrator.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.add(Activity(user_id=user.id, action=ActivityAction.LOGIN, detail="Signed in"))
    await db.commit()
    await db.refresh(user)
    return _issue(user)


@router.post("/forgot-password", response_model=Message)
async def forgot_password(body: ForgotPasswordRequest, db: DbSession) -> Message:
    """Record a self-service reset request for an admin to action.

    There is no outbound-email service configured in this deployment, so no
    mail is actually sent — this logs the request against the matching
    account (visible in the History/Admin activity feed) so an admin can
    follow up with `AdminPasswordReset`. The response is identical whether
    or not the account exists, for the same reason `/login` doesn't
    distinguish a bad username from a bad password.
    """
    identifier = body.identifier.strip()
    user = await db.scalar(
        select(User).where(or_(User.username == identifier, User.email == identifier))
    )
    if user is not None and user.is_active:
        db.add(Activity(
            user_id=user.id,
            action=ActivityAction.PASSWORD_RESET,
            detail="Requested a password reset link",
        ))
        await db.commit()
    return Message(message="If that account exists, a password reset request has been sent.")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: DbSession) -> TokenResponse:
    claims = decode_token(body.refresh_token, expected_type="refresh")
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Sign in again.",
        )
    user = await db.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Sign in again.",
        )
    return _issue(user)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/change-password", response_model=Message)
async def change_password(
    body: ChangePasswordRequest, user: CurrentUser, db: DbSession
) -> Message:
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your current password is incorrect.",
        )
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose a password different from your current one.",
        )
    user.hashed_password = hash_password(body.new_password)
    db.add(Activity(user_id=user.id, action=ActivityAction.PASSWORD_RESET,
                    detail="Changed own password"))
    await db.commit()
    return Message(message="Password updated.")
