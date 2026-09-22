"""Team and per-team Claude API key configuration.

One row per team (unique constraint on `team`) — no versioning. An Admin
rotating a team's key updates `api_key_encrypted` on that same row in place,
so `claude_config_id` recorded on a Batch/ApiUsage row never dangles or needs
migrating; it simply keeps pointing at "this team's configuration", whatever
key currently lives there. See app/services/claude_config.py.
"""
import enum

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Team(str, enum.Enum):
    CHENNAI = "CHENNAI"
    HYDERABAD = "HYDERABAD"
    QATAR = "QATAR"


class ClaudeApiConfig(Base, TimestampMixin):
    __tablename__ = "claude_api_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    team: Mapped[Team] = mapped_column(
        Enum(Team, name="claude_config_team", values_callable=lambda e: [m.value for m in e]),
        unique=True, nullable=False,
    )
    # Fernet ciphertext (see app/services/claude_config.py) — the plaintext
    # key is never stored and never leaves the backend once encrypted.
    api_key_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
