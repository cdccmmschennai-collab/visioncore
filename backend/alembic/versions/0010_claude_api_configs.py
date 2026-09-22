"""claude_api_configs: one Claude API key configuration per team, encrypted
at rest (see app/services/claude_config.py). Seeds CHENNAI from the existing
ANTHROPIC_API_KEY env var so an existing install keeps working immediately
without the Admin re-entering it — HYD and QA are then configured from the
new Admin -> Claude API Settings page.

Revision ID: 0010
Revises: 0009
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

claude_config_team = postgresql.ENUM(
    "CHENNAI", "HYD", "QA", name="claude_config_team", create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "claude_api_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team", claude_config_team, nullable=False),
        sa.Column("api_key_encrypted", sa.String(512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "updated_by_user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("team", name="uq_claude_api_configs_team"),
    )

    # Same encryption scheme app/services/claude_config.py uses at runtime,
    # imported here (not reimplemented) so the seeded row decrypts cleanly.
    from app.core.config import settings
    from app.services.claude_config import encrypt_api_key

    if settings.anthropic_api_key:
        op.execute(
            sa.text(
                "INSERT INTO claude_api_configs (team, api_key_encrypted, is_active, created_at, updated_at) "
                "VALUES ('CHENNAI', :key, true, now(), now())"
            ).bindparams(key=encrypt_api_key(settings.anthropic_api_key))
        )


def downgrade() -> None:
    op.drop_table("claude_api_configs")
