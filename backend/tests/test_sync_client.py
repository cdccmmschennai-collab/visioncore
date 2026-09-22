"""Unit tests for the sync client's row-coercion and safety-column logic.

No database or network is exercised here — this project has no
pytest-asyncio dependency and none is added for this. The one genuinely
async piece worth covering, the sync-token auth gate, is run directly via
asyncio.run(), matching the plain-pytest style of test_filename_parser.py.
"""
import asyncio
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core import deps
from app.core.config import settings
from app.models import User, UserRole
from app.models import AssetTag, Batch
from app.services.sync_client import (
    _CONFLICT_COLUMN,
    _PROTECTED_COLUMNS,
    _UNUSABLE_PASSWORD_HASH,
    _coerce_row,
    _updatable_columns,
    push_user,
)


def test_coerce_row_parses_iso_datetimes_for_the_asyncpg_driver():
    row = {
        "id": 1,
        "username": "alice",
        "created_at": "2026-01-15T10:30:00+00:00",
        "updated_at": "2026-01-15T10:30:00+00:00",
    }
    values = _coerce_row(User.__table__, row)
    assert values["created_at"] == datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc)
    assert values["updated_at"] == datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc)
    assert values["id"] == 1
    assert values["username"] == "alice"


def test_coerce_row_passes_through_none_and_drops_unknown_keys():
    row = {"id": 2, "email": None, "not_a_real_column": "ignored"}
    assert _coerce_row(User.__table__, row) == {"id": 2, "email": None}


def test_user_credentials_are_never_overwritten_by_a_sync_upsert():
    assert _PROTECTED_COLUMNS[User] == frozenset({"hashed_password", "last_login_at"})


def test_updatable_columns_never_includes_a_column_absent_from_the_payload():
    # Regression test: a column the sender's Sync*Out schema doesn't include
    # (e.g. `team`, added to the users table after schemas/sync.py's
    # SyncUserOut was last updated) must NOT appear in the UPDATE SET
    # clause — including it would resolve to that column's DEFAULT via
    # Postgres's `excluded` pseudo-row (it was never in the INSERT's value
    # list), silently resetting an existing row's real value on every future
    # sync upsert. This is exactly what happened to users.team in practice.
    values = {"id": 5, "username": "HYD_User", "email": None}
    cols = _updatable_columns(values, frozenset())
    assert "team" not in cols
    assert set(cols) == {"username", "email"}


def test_updatable_columns_excludes_id_and_protected_columns():
    values = {"id": 5, "username": "x", "hashed_password": "y", "last_login_at": None}
    cols = _updatable_columns(values, _PROTECTED_COLUMNS[User])
    assert set(cols) == {"username"}


def test_user_upserts_by_username_not_id():
    # Regression test: users can be created independently on both
    # production and this local mirror (push_user runs both directions —
    # see sync_client.push_user and app/api/v1/sync.py::push_user), so each
    # side auto-assigns its own id from its own sequence. The SAME username
    # can therefore land under two different ids across environments —
    # upserting by id would create a duplicate-username row (or collide
    # with uq_users_username) instead of recognizing it as the same account.
    assert _CONFLICT_COLUMN[User] == "username"


def test_every_other_synced_resource_still_upserts_by_id():
    # Every resource except User is only ever created by pulling from
    # production (a genuinely pure mirror — see module docstring), so
    # upserting by id remains correct and unchanged for them.
    assert _CONFLICT_COLUMN.get(AssetTag, "id") == "id"
    assert _CONFLICT_COLUMN.get(Batch, "id") == "id"


def test_placeholder_password_can_never_be_used_to_log_in():
    # Not a real bcrypt hash, so verify_password() can never match it —
    # a synced-only account must be unusable until an admin sets a password.
    assert not _UNUSABLE_PASSWORD_HASH.startswith("$2b$")


def test_sync_endpoints_reject_a_wrong_token(monkeypatch):
    monkeypatch.setattr(deps.settings, "sync_api_token", "correct-token")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong-token")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(deps.require_sync_token(creds))
    assert exc.value.status_code == 401


def test_sync_endpoints_reject_a_missing_token(monkeypatch):
    monkeypatch.setattr(deps.settings, "sync_api_token", "correct-token")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(deps.require_sync_token(None))
    assert exc.value.status_code == 401


def test_sync_endpoints_fail_closed_when_unconfigured(monkeypatch):
    monkeypatch.setattr(deps.settings, "sync_api_token", "")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="anything")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(deps.require_sync_token(creds))
    assert exc.value.status_code == 503


def test_sync_endpoints_accept_the_correct_token(monkeypatch):
    monkeypatch.setattr(deps.settings, "sync_api_token", "correct-token")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="correct-token")
    asyncio.run(deps.require_sync_token(creds))  # does not raise


def test_push_user_is_a_noop_when_sync_is_not_configured(monkeypatch):
    # This side only ever pushes when it's also the puller (SYNC_SOURCE_URL
    # set); production leaves both unset, so it must never try to push here.
    monkeypatch.setattr(settings, "sync_source_url", "")
    monkeypatch.setattr(settings, "sync_api_token", "")
    user = User(id=1, username="alice", role=UserRole.USER, is_active=True)
    asyncio.run(push_user(user))  # does not raise, makes no request
