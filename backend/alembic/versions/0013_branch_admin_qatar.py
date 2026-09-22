"""Branch-based Admin access control.

Two additive, data-preserving changes — nothing is dropped or reset:

1. Renames the "QA" team value to "QATAR" on the shared claude_config_team
   enum. This is a rename, not a new team: every row that already carries
   team='QA' (users, batches, api_usage, claude_api_configs — the enum is
   shared across all four) transparently becomes team='QATAR', in place.
   ALTER TYPE ... RENAME VALUE is transactional and touches only the type's
   catalog entry, not the columns/rows using it.
2. Adds 'branch_admin' to user_role, alongside the existing 'admin' (which
   now means "Overall Admin" — unchanged behavior/value) and 'user'. No
   existing user's role changes; this migration does not create or promote
   any account. An Overall Admin creates branch admins afterward, from the
   Admin UI, same as any other user.

Revision ID: 0013
Revises: 0012
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE claude_config_team RENAME VALUE 'QA' TO 'QATAR'")
    # Postgres 12+ allows ALTER TYPE ... ADD VALUE inside a transaction; the
    # new label just can't be referenced by the same statement that adds it,
    # which isn't an issue here since nothing else in this migration uses it
    # (same pattern as migration 0007's item_status 'retrying' addition).
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'branch_admin'")


def downgrade() -> None:
    # Renaming back is safe and reversible.
    op.execute("ALTER TYPE claude_config_team RENAME VALUE 'QATAR' TO 'QA'")
    # Postgres has no ALTER TYPE ... DROP VALUE — same one-way, additive
    # treatment as every other enum-value addition in this project (see
    # migration 0007's downgrade comment). Any user actually holding
    # role='branch_admin' at downgrade time would need manual reassignment
    # first; this migration never creates one itself.
