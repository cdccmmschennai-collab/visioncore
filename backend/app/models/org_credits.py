from sqlalchemy import Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class OrgCredits(Base, TimestampMixin):
    """A single admin-entered figure: the organization's available Claude API
    credit balance, as last seen on the Claude Console Billing page.

    Anthropic's official API has no endpoint for organization credit balance
    on Claude Console/Platform orgs, so this is deliberately not fetched or
    calculated — an admin types in what the Console shows, and it's
    displayed as-is (plus an INR conversion) until next updated. Single-row
    table: always id=1.
    """
    __tablename__ = "org_credits"

    id: Mapped[int] = mapped_column(primary_key=True)
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
