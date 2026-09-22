"""batches.team + batches.claude_config_id — snapshot the uploading user's
team and their team's current Claude configuration at creation time (see
app/services/batch_ingest.py), so an Admin rotating a key later never
changes which config an already-created batch is attributed to.

Existing batches are backfilled from their owning user's team (known as of
migration 0009) for reporting consistency. claude_config_id is left null for
them — there's no historical per-team config to point at; only a batch
created after this feature ships gets a real snapshot.

Revision ID: 0011
Revises: 0010
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

claude_config_team = postgresql.ENUM(
    "CHENNAI", "HYD", "QA", name="claude_config_team", create_type=False,
)


def upgrade() -> None:
    op.add_column(
        "batches",
        sa.Column("team", claude_config_team, nullable=False, server_default="CHENNAI"),
    )
    op.add_column(
        "batches",
        sa.Column(
            "claude_config_id", sa.Integer(),
            sa.ForeignKey("claude_api_configs.id", ondelete="SET NULL"), nullable=True,
        ),
    )
    op.execute(
        "UPDATE batches SET team = users.team FROM users WHERE batches.user_id = users.id"
    )


def downgrade() -> None:
    op.drop_column("batches", "claude_config_id")
    op.drop_column("batches", "team")
