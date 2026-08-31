"""Per-resource pull position for the local <- production sync client.

Lives on whichever database runs the puller (the local/mirror side). On
production this table exists but stays empty — production never pulls from
anywhere, it only serves `app/api/v1/sync.py` to whoever asks.
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SyncCursor(Base, TimestampMixin):
    __tablename__ = "sync_cursors"

    resource: Mapped[str] = mapped_column(String(32), primary_key=True)
    since_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    since_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
