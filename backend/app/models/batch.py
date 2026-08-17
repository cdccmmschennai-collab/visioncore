import enum

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


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

    user = relationship("User", back_populates="batches")
    items = relationship(
        "BatchItem",
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="BatchItem.id",
    )
