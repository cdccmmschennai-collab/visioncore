"""Password hashing and JWT issuance/verification."""
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(plain: str) -> str:
    # bcrypt caps at 72 bytes; truncate deterministically rather than raising.
    return pwd_context.hash(plain[:72])


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain[:72], hashed)
    except ValueError:
        return False


def create_token(subject: str | int, token_type: TokenType, **extra: Any) -> str:
    now = datetime.now(timezone.utc)
    if token_type == "access":
        expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    else:
        expires = now + timedelta(days=settings.refresh_token_expire_days)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        **extra,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any] | None:
    """Return the claims, or None if the token is invalid, expired, or the wrong type."""
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if expected_type and claims.get("type") != expected_type:
        return None
    return claims


def create_link_token(claims: dict[str, Any], expires_in: timedelta) -> str:
    """A signed, self-contained capability token for a hyperlink in an exported
    file (see app.services.download_links) — distinct from create_token's
    access/refresh pair, which are bound to a login session, not a resource.
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        **claims,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_in).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_link_token(token: str) -> dict[str, Any] | None:
    """Return the claims, or None if the token is invalid, tampered with, or expired."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
