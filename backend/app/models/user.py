import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.claude_config import Team


class UserRole(str, enum.Enum):
    #: Overall Admin — unrestricted, every branch. Value/meaning unchanged
    #: from before branch admins existed.
    ADMIN = "admin"
    #: Branch Admin — scoped to exactly this account's own `team`. See
    #: app/core/deps.py's AnyAdminUser/team_scope for how that's enforced.
    BRANCH_ADMIN = "branch_admin"
    USER = "user"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        default=UserRole.USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Which Claude API configuration (app/models/claude_config.py) this
    # user's extractions route through — never inferred from username, only
    # ever this column. See app/services/ai_extractor.py. For a BRANCH_ADMIN
    # this is also their access scope (see app/core/deps.py); for a plain
    # USER it's just their extraction routing. Meaningless/"don't care" for
    # an (Overall) ADMIN — deliberately not made nullable for that case, to
    # avoid a schema change just to represent "N/A" for one role.
    team: Mapped[Team] = mapped_column(
        Enum(Team, name="claude_config_team", values_callable=lambda e: [m.value for m in e]),
        default=Team.CHENNAI, server_default=Team.CHENNAI.value, nullable=False,
    )

    batches = relationship("Batch", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN
