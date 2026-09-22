"""Make uq_users_email DEFERRABLE INITIALLY IMMEDIATE.

Same reasoning as migration 0008's uq_asset_tags_tag_number: default check
timing is unchanged (still immediate everywhere else) — this only lets
app/services/sync_client.py's sync transaction (which already issues `SET
CONSTRAINTS ALL DEFERRED` before every page) defer the check to COMMIT, as
defense-in-depth against an email ending up transiently duplicated across
two different-username rows mid-page.

uq_users_username is deliberately left NOT deferrable: Postgres does not
allow a deferrable unique constraint to serve as an ON CONFLICT arbiter, and
app/services/sync_client.py upserts User rows via `ON CONFLICT (username)`
specifically (see _CONFLICT_COLUMN) — the real fix for a username colliding
across two different ids (production and this local mirror can each
independently create a user, auto-assigning their own id) is upserting by
username, not deferring the check.

Revision ID: 0015
Revises: 0014
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.create_unique_constraint(
        "uq_users_email", "users", ["email"],
        deferrable=True, initially="IMMEDIATE",
    )


def downgrade() -> None:
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.create_unique_constraint("uq_users_email", "users", ["email"])
