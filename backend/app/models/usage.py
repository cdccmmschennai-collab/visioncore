from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.claude_config import Team


class ApiUsage(Base, TimestampMixin):
    """One row per Claude API call.

    Anthropic exposes no live balance endpoint, so spend is *measured* here from
    each response's usage block and priced with the rates in settings. The admin
    dashboard totals these against CLAUDE_CREDIT_BUDGET_USD.
    """
    __tablename__ = "api_usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    tag_number: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Denormalized from the batch this extraction belonged to (see
    # pipeline.py) so a team-usage report (Admin -> Claude usage) never
    # needs to join through batches/batch_items. Nullable: rows recorded
    # before this feature existed are backfilled to CHENNAI by migration
    # 0012, but a future row is always stamped.
    team: Mapped[Team | None] = mapped_column(
        Enum(Team, name="claude_config_team", values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    claude_config_id: Mapped[int | None] = mapped_column(
        ForeignKey("claude_api_configs.id", ondelete="SET NULL"), nullable=True
    )
