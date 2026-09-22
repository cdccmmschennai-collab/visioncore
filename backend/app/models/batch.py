import enum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.claude_config import Team


class BatchStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"      # some tags completed, some failed


class Batch(Base, TimestampMixin):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[BatchStatus] = mapped_column(
        Enum(BatchStatus, name="batch_status", values_callable=lambda e: [m.value for m in e]),
        default=BatchStatus.UPLOADED,
        nullable=False,
    )
    total_images: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tags: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # True only for a batch created via POST /batches/batch-process (a
    # browser-scanned local folder — see frontend/src/utils/folderAccess.ts),
    # never for a normal drag-drop upload.
    is_batch_process: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    # Snapshot of the uploading user's team at creation time (see
    # app/services/batch_ingest.py) — extraction routes on this, not on
    # current_user, so it's correct even from a Celery worker with no
    # request/session context.
    team: Mapped[Team] = mapped_column(
        Enum(Team, name="claude_config_team", values_callable=lambda e: [m.value for m in e]),
        default=Team.CHENNAI, server_default=Team.CHENNAI.value, nullable=False,
    )
    # The team's active ClaudeApiConfig at the moment this batch was
    # created (or first successfully extracted, if none was configured yet
    # — see pipeline.process_item's lazy backfill). Frozen once set: an
    # Admin rotating the key later updates that config row in place rather
    # than creating a new one, so this id is never repointed. Null only for
    # a batch whose team still has no configured key. SET NULL (not
    # RESTRICT) so deleting a config row is never blocked by old batches.
    claude_config_id: Mapped[int | None] = mapped_column(
        ForeignKey("claude_api_configs.id", ondelete="SET NULL"), nullable=True
    )

    user = relationship("User", back_populates="batches")
    items = relationship(
        "BatchItem",
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="BatchItem.id",
    )
