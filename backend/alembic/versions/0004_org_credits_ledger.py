"""Turn org_credits from an admin-typed "current balance" into an estimated
balance: total purchased (running total, incremented per top-up) minus a
ledger of Anthropic's own reported usage. See services/org_credits.py.

Revision ID: 0004
Revises: 0003
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("org_credits", "amount_usd", new_column_name="total_purchased_usd")
    op.add_column(
        "org_credits",
        sa.Column("ledger_usage_usd", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column("org_credits", sa.Column("ledger_through_date", sa.Date(), nullable=True))
    op.alter_column("org_credits", "ledger_usage_usd", server_default=None)


def downgrade() -> None:
    op.drop_column("org_credits", "ledger_through_date")
    op.drop_column("org_credits", "ledger_usage_usd")
    op.alter_column("org_credits", "total_purchased_usd", new_column_name="amount_usd")
