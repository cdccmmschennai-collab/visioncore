"""Team-scoped Claude API key configuration: encryption, lookup, admin CRUD.

One row per team (see app/models/claude_config.py) — no versioning. Looking
up a team's key is always "the current row for that team", which is exactly
what makes app/services/ai_extractor.py correct with zero caching: it reads
straight from here on every extraction, so an Admin's key rotation takes
effect on the very next call, in any process (including a Celery worker).
"""
from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import ClaudeApiConfig, Team

logger = logging.getLogger(__name__)


class ClaudeConfigError(RuntimeError):
    """No active Claude API configuration exists for a team."""


def _fernet() -> Fernet:
    # Any string is accepted for CLAUDE_KEY_ENCRYPTION_SECRET — this derives
    # a valid 32-byte Fernet key from it rather than requiring the admin to
    # generate one themselves.
    secret = settings.claude_key_encryption_secret or settings.jwt_secret
    derived = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(derived)


def encrypt_api_key(raw_key: str) -> str:
    return _fernet().encrypt(raw_key.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    try:
        return _fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken as exc:
        # Never happens from our own writes; only from a mismatched/changed
        # CLAUDE_KEY_ENCRYPTION_SECRET. Never include the ciphertext in the
        # message — it's still secret-derived even though it won't decrypt.
        raise ClaudeConfigError(
            "Stored Claude API key could not be decrypted — "
            "CLAUDE_KEY_ENCRYPTION_SECRET may have changed."
        ) from exc


def mask_api_key(raw_key: str) -> str:
    """e.g. sk-ant-api03-... -> sk-ant-••••••••••••1234 — never enough to
    reconstruct the key. A key too short to safely reveal a prefix/suffix
    from (malformed/legacy) is masked entirely instead."""
    prefix, suffix = raw_key[:7], raw_key[-4:]
    if len(raw_key) < len(prefix) + len(suffix) + 4:
        return "sk-ant-" + "•" * 8
    return f"{prefix}{'•' * 12}{suffix}"


async def get_active_config(db: AsyncSession, team: Team) -> ClaudeApiConfig | None:
    return await db.scalar(
        select(ClaudeApiConfig).where(ClaudeApiConfig.team == team, ClaudeApiConfig.is_active.is_(True))
    )


async def get_decrypted_key(db: AsyncSession, team: Team) -> tuple[str, int]:
    """Returns (api_key, claude_config_id). Raises ClaudeConfigError if the
    team has no active configuration — callers must not fall back to
    another team's key."""
    config = await get_active_config(db, team)
    if config is None:
        raise ClaudeConfigError(f"Claude API is not configured for the {team.value} team.")
    return decrypt_api_key(config.api_key_encrypted), config.id


async def set_api_key(db: AsyncSession, team: Team, raw_key: str, admin_id: int) -> ClaudeApiConfig:
    """Create or update the one row for `team`. Does not commit — the caller
    owns the transaction (matches every other admin.py write)."""
    config = await db.scalar(select(ClaudeApiConfig).where(ClaudeApiConfig.team == team))
    encrypted = encrypt_api_key(raw_key)
    if config is None:
        config = ClaudeApiConfig(
            team=team, api_key_encrypted=encrypted, is_active=True, updated_by_user_id=admin_id,
        )
        db.add(config)
    else:
        config.api_key_encrypted = encrypted
        config.is_active = True
        config.updated_by_user_id = admin_id
    await db.flush()
    return config


async def test_connection(raw_key: str) -> tuple[bool, str]:
    """A minimal, cheap Anthropic call (max_tokens=1) to verify a key
    actually works. Never logs or returns the key itself."""
    from anthropic import APIConnectionError, APIStatusError, AsyncAnthropic

    client = AsyncAnthropic(api_key=raw_key, max_retries=0, timeout=15.0)
    try:
        await client.messages.create(
            model=settings.claude_model, max_tokens=1,
            messages=[{"role": "user", "content": "Reply with OK."}],
        )
        return True, "Connected successfully."
    except APIConnectionError:
        return False, "Could not reach the Claude API."
    except APIStatusError as exc:
        if exc.status_code == 401:
            return False, "Invalid API key."
        return False, f"Connection failed (HTTP {exc.status_code})."
    except Exception:                                      # noqa: BLE001 - last resort
        logger.exception("Claude test connection failed unexpectedly")
        return False, "Connection failed."
    finally:
        await client.close()
