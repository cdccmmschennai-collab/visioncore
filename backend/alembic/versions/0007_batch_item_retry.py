"""Add ItemStatus.RETRYING (additive enum value) and batch_items.retry_count,
for queue-based concurrent batch processing (see app/services/pipeline.py).

Revision ID: 0007
Revises: 0006
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres 12+ allows ALTER TYPE ... ADD VALUE inside a transaction; the
    # new label just can't be referenced by the same statement that adds it,
    # which isn't an issue here since nothing else in this migration uses it.
    op.execute("ALTER TYPE item_status ADD VALUE IF NOT EXISTS 'retrying'")

    op.add_column(
        "batch_items",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("batch_items", "retry_count")
    # Postgres has no ALTER TYPE ... DROP VALUE. Removing 'retrying' would
    # require rebuilding the enum type (rename, recreate, cast every column,
    # drop the old type) — deliberately not done here; this migration's
    # enum-value addition is treated as a one-way, additive change, same as
    # every other ItemStatus/BatchStatus value already in the schema.
