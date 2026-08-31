"""Wire format for the production -> local sync endpoints (app/api/v1/sync.py)
and client (app/services/sync_client.py).

Deliberately separate from the UI-facing schemas in schemas/tag.py: the sync
wire format mirrors the ORM columns directly (including internal FKs like
edited_by_id, and both created_at/updated_at for cursoring), which is a
different contract than what the results table needs. Keeping them apart
means either one can change without touching the other.
"""
from datetime import datetime

from pydantic import BaseModel

from app.models.activity import ActivityAction
from app.models.batch import BatchStatus
from app.models.tag import ItemStatus
from app.models.user import UserRole
from app.schemas.common import ORMModel


class SyncUserOut(ORMModel):
    id: int
    username: str
    email: str | None = None
    full_name: str | None = None
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # hashed_password is intentionally never included here — credentials
    # never leave production. See sync_client._row_values.


class SyncUserPush(BaseModel):
    """Local -> production: a user created on the local/mirror Admin page,
    pushed so it also exists on production. See app/services/sync_client.py
    ::push_user (sender) and app/api/v1/sync.py::push_user (receiver).

    No password field, by design — see the receiver's handling.
    """
    username: str
    email: str | None = None
    full_name: str | None = None
    role: UserRole
    is_active: bool


class SyncBatchOut(ORMModel):
    id: int
    reference: str
    user_id: int
    status: BatchStatus
    total_images: int
    total_tags: int
    created_at: datetime
    updated_at: datetime


class SyncBatchItemOut(ORMModel):
    id: int
    batch_id: int
    asset_tag_id: int | None = None
    tag_number: str
    description: str
    status: ItemStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class SyncAssetTagOut(ORMModel):
    id: int
    tag_number: str
    description: str
    ai_payload: dict
    final_payload: dict
    ai_excel_path: str | None = None
    template_excel_path: str | None = None
    edited_by_id: int | None = None
    created_by_id: int | None = None
    revision: int
    created_at: datetime
    updated_at: datetime


class SyncTagImageOut(ORMModel):
    id: int
    item_id: int
    original_filename: str
    stored_path: str
    media_type: str
    size_bytes: int
    content_hash: str | None = None
    created_at: datetime
    updated_at: datetime


class SyncActivityOut(ORMModel):
    id: int
    user_id: int | None = None
    action: ActivityAction
    tag_number: str | None = None
    description: str | None = None
    detail: str | None = None
    meta: dict
    created_at: datetime
    updated_at: datetime
