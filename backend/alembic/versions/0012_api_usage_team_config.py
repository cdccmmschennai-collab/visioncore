"""api_usage.team + api_usage.claude_config_id — lets Admin -> Claude usage
report per-team extraction cost/tokens (GET /admin/usage/by-team) without
joining through batches/batch_items on every request.

Existing rows are backfilled from their user's team for reporting
continuity; claude_config_id stays null for them (no historical config to
attribute to). A row whose user_id is already null (the user was later
deleted — see ApiUsage.user_id's ON DELETE SET NULL) defaults to CHENNAI,
the only team that existed before this feature.

Revision ID: 0012
Revises: 0011
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

claude_config_team = postgresql.ENUM(
    "CHENNAI", "HYD", "QA", name="claude_config_team", create_type=False,
)


def upgrade() -> None:
    op.add_column("api_usage", sa.Column("team", claude_config_team, nullable=True))
    op.add_column(
        "api_usage",
        sa.Column(
            "claude_config_id", sa.Integer(),
            sa.ForeignKey("claude_api_configs.id", ondelete="SET NULL"), nullable=True,
        ),
    )
    op.execute(
        "UPDATE api_usage SET team = users.team FROM users "
        "WHERE api_usage.user_id = users.id AND api_usage.team IS NULL"
    )
    op.execute("UPDATE api_usage SET team = 'CHENNAI' WHERE team IS NULL")


def downgrade() -> None:
    op.drop_column("api_usage", "claude_config_id")
    op.drop_column("api_usage", "team")
