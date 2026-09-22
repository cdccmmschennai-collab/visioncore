"""Make uq_asset_tags_tag_number DEFERRABLE INITIALLY IMMEDIATE.

Default check timing is unchanged (still immediate, same as today) — this
only allows a transaction to opt into deferring the check to COMMIT via
`SET CONSTRAINTS uq_asset_tags_tag_number DEFERRED`, which
app/services/sync_client.py now does. Needed because a sync page can contain
a chain of tag_number edits/swaps across several rows (production allows
editing an existing tag's number) — replaying it in id order can transiently
collide with another row's not-yet-updated value even though the page's
final state is valid. app/services/pipeline.py's race-proof duplicate
detection (a plain flush(), no SET CONSTRAINTS) is unaffected since it never
requests deferred checking.

Revision ID: 0008
Revises: 0007
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_asset_tags_tag_number", "asset_tags", type_="unique")
    op.create_unique_constraint(
        "uq_asset_tags_tag_number", "asset_tags", ["tag_number"],
        deferrable=True, initially="IMMEDIATE",
    )


def downgrade() -> None:
    op.drop_constraint("uq_asset_tags_tag_number", "asset_tags", type_="unique")
    op.create_unique_constraint("uq_asset_tags_tag_number", "asset_tags", ["tag_number"])
