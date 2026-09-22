"""Add users.team (CHENNAI/HYD/QA) — per-team Claude API key routing.

The one-time UPDATEs below for HYD_User -> HYD and QA_User -> QA are a data
backfill matching this feature's known launch state, not routing logic —
app code (app/services/ai_extractor.py) always reads User.team, never a
username.

Revision ID: 0009
Revises: 0008
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Shared by every table that carries a team (users, batches, api_usage,
# claude_api_configs) — created once here, referenced with create_type=False
# everywhere else. See alembic/versions/0001_initial_schema.py for why
# postgresql.ENUM (not generic sa.Enum) is required for that to work.
claude_config_team = postgresql.ENUM(
    "CHENNAI", "HYD", "QA", name="claude_config_team", create_type=False,
)


def upgrade() -> None:
    claude_config_team.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column("team", claude_config_team, nullable=False, server_default="CHENNAI"),
    )
    op.execute("UPDATE users SET team = 'HYD' WHERE username = 'HYD_User'")
    op.execute("UPDATE users SET team = 'QA' WHERE username = 'QA_User'")


def downgrade() -> None:
    op.drop_column("users", "team")
    claude_config_team.drop(op.get_bind(), checkfirst=True)
