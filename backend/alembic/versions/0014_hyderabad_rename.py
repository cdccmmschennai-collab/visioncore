"""Rename the "HYD" team value to "HYDERABAD" — matches CHENNAI/QATAR being
full location names rather than an abbreviation. Same data-preserving
approach as migration 0013's QA -> QATAR rename: ALTER TYPE ... RENAME VALUE
transparently relabels every row already carrying team='HYD' (users,
batches, api_usage, claude_api_configs share this one enum) to 'HYDERABAD'
in place — nothing is dropped, reset, or re-inserted.

Revision ID: 0014
Revises: 0013
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE claude_config_team RENAME VALUE 'HYD' TO 'HYDERABAD'")


def downgrade() -> None:
    op.execute("ALTER TYPE claude_config_team RENAME VALUE 'HYDERABAD' TO 'HYD'")
