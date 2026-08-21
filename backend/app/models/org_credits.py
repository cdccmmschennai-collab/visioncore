from datetime import date

from sqlalchemy import Date, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class OrgCredits(Base, TimestampMixin):
    """Estimated Claude API credit balance: purchased credits minus tracked usage.

    Anthropic's official API has no endpoint for the account's actual credit
    balance on Claude Console/Platform orgs — only historical usage/cost. So
    instead of a fetched balance, an admin records what was purchased
    (`total_purchased_usd`, a running total incremented by each top-up), and
    the app tracks Anthropic's own reported spend into a ledger
    (`ledger_usage_usd`, advanced one *closed* day at a time up through
    `ledger_through_date`) so the estimate survives the Cost API's ~31-day
    reporting window instead of losing older days as they roll off it.

    Estimated Balance = total_purchased_usd - tracked usage (the ledger, plus
    today's still-open day recomputed fresh on every read — see
    services/org_credits.py). Single-row table: always id=1.
    """
    __tablename__ = "org_credits"

    id: Mapped[int] = mapped_column(primary_key=True)
    total_purchased_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    #: Anthropic spend already folded in, for every day through
    #: `ledger_through_date` inclusive. Only ever grows, and only by whole
    #: closed days, so a day already counted is never counted again even
    #: though Anthropic's own report re-sends it on every subsequent call.
    ledger_usage_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ledger_through_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
