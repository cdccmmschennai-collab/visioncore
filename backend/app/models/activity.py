import enum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ActivityAction(str, enum.Enum):
    LOGIN = "login"
    UPLOAD = "upload"
    EXTRACT = "extract"
    EDIT = "edit"
    DOWNLOAD = "download"
    DUPLICATE_BLOCKED = "duplicate_blocked"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    PASSWORD_RESET = "password_reset"


class Activity(Base, TimestampMixin):
    """Append-only audit trail. Powers the History page and the admin view."""
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    action: Mapped[ActivityAction] = mapped_column(
        Enum(ActivityAction, name="activity_action", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        index=True,
    )
    tag_number: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    user = relationship("User", back_populates="activities")
