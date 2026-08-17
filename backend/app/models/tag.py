import enum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ItemStatus(str, enum.Enum):
    """Per-tag pipeline state, mirrored one-for-one in the UI status rail."""
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DUPLICATE = "duplicate"


class AssetTag(Base, TimestampMixin):
    """The canonical, de-duplicated record for one physical asset tag.

    `tag_number` carries a unique constraint — this is what makes the duplicate
    check race-proof. Two concurrent batches containing the same tag will have
    one INSERT succeed and the other raise IntegrityError, which the pipeline
    catches and reports as a duplicate rather than a failure.
    """
    __tablename__ = "asset_tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    tag_number: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    # Claude's untouched answer — never overwritten, so an audit can always
    # compare what the model said against what the reviewer accepted.
    ai_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # The reviewed/edited values that drive both workbooks.
    final_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    ai_excel_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    template_excel_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    edited_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    items = relationship("BatchItem", back_populates="asset_tag")


class BatchItem(Base, TimestampMixin):
    """One tag *within one batch* — carries the per-run status and error."""
    __tablename__ = "batch_items"
    __table_args__ = (UniqueConstraint("batch_id", "tag_number", name="uq_batch_tag"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("batches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    asset_tag_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_tags.id", ondelete="SET NULL"), nullable=True
    )
    tag_number: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ItemStatus] = mapped_column(
        Enum(ItemStatus, name="item_status", values_callable=lambda e: [m.value for m in e]),
        default=ItemStatus.UPLOADED,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    batch = relationship("Batch", back_populates="items")
    asset_tag = relationship("AssetTag", back_populates="items")
    images = relationship(
        "TagImage", back_populates="item", cascade="all, delete-orphan", order_by="TagImage.id"
    )


class TagImage(Base, TimestampMixin):
    __tablename__ = "tag_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("batch_items.id", ondelete="CASCADE"), index=True, nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(512), nullable=False)
    media_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # SHA-256 of the file's bytes. Two uploads with the same content share one
    # stored_path — this is what a repeat upload is matched against.
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    item = relationship("BatchItem", back_populates="images")
