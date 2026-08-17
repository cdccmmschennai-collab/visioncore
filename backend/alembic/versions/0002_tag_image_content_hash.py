"""Add content_hash to tag_images, for content-based upload de-duplication.

Revision ID: 0002
Revises: 0001
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tag_images", sa.Column("content_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_tag_images_content_hash", "tag_images", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_tag_images_content_hash", table_name="tag_images")
    op.drop_column("tag_images", "content_hash")
