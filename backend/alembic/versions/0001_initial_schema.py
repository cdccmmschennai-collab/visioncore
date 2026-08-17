"""Initial schema: users, batches, asset tags, images, activity, api usage.

Revision ID: 0001
Revises:
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# postgresql.ENUM (not the generic sa.Enum) is required here: only the
# dialect-specific type honors create_type=False. With the generic sa.Enum,
# create_type is silently dropped, so op.create_table() re-issues CREATE
# TYPE on top of the explicit one below and fails with "already exists".
user_role = postgresql.ENUM("admin", "user", name="user_role", create_type=False)
batch_status = postgresql.ENUM(
    "uploaded", "processing", "completed", "failed", "partial",
    name="batch_status", create_type=False,
)
item_status = postgresql.ENUM(
    "uploaded", "extracting", "processing", "completed", "failed", "duplicate",
    name="item_status", create_type=False,
)
activity_action = postgresql.ENUM(
    "login", "upload", "extract", "edit", "download", "duplicate_blocked",
    "user_created", "user_updated", "password_reset",
    name="activity_action", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (user_role, batch_status, item_status, activity_action):
        enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(128), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reference", sa.String(32), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", batch_status, nullable=False, server_default="uploaded"),
        sa.Column("total_images", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tags", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("reference", name="uq_batches_reference"),
    )
    op.create_index("ix_batches_reference", "batches", ["reference"])
    op.create_index("ix_batches_user_id", "batches", ["user_id"])

    op.create_table(
        "asset_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tag_number", sa.String(128), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("ai_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("final_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("ai_excel_path", sa.String(512), nullable=True),
        sa.Column("template_excel_path", sa.String(512), nullable=True),
        sa.Column("edited_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # The duplicate check depends on this constraint, not on the SELECT
        # that precedes it — that SELECT is an optimisation, this is the rule.
        sa.UniqueConstraint("tag_number", name="uq_asset_tags_tag_number"),
    )
    op.create_index("ix_asset_tags_tag_number", "asset_tags", ["tag_number"])

    op.create_table(
        "batch_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_tag_id", sa.Integer(), sa.ForeignKey("asset_tags.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tag_number", sa.String(128), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("status", item_status, nullable=False, server_default="uploaded"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("batch_id", "tag_number", name="uq_batch_tag"),
    )
    op.create_index("ix_batch_items_batch_id", "batch_items", ["batch_id"])
    op.create_index("ix_batch_items_tag_number", "batch_items", ["tag_number"])

    op.create_table(
        "tag_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("batch_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("stored_path", sa.String(512), nullable=False),
        sa.Column("media_type", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tag_images_item_id", "tag_images", ["item_id"])

    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("action", activity_action, nullable=False),
        sa.Column("tag_number", sa.String(128), nullable=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("detail", sa.String(512), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_activities_user_id", "activities", ["user_id"])
    op.create_index("ix_activities_action", "activities", ["action"])
    op.create_index("ix_activities_tag_number", "activities", ["tag_number"])
    # History is always read newest-first; this index serves that ORDER BY.
    op.create_index("ix_activities_created_at", "activities", [sa.text("created_at DESC")])

    op.create_table(
        "api_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tag_number", sa.String(128), nullable=True),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_api_usage_user_id", "api_usage", ["user_id"])
    op.create_index("ix_api_usage_tag_number", "api_usage", ["tag_number"])
    op.create_index("ix_api_usage_created_at", "api_usage", ["created_at"])


def downgrade() -> None:
    for table in ("api_usage", "activities", "tag_images", "batch_items",
                  "asset_tags", "batches", "users"):
        op.drop_table(table)
    bind = op.get_bind()
    for enum in (activity_action, item_status, batch_status, user_role):
        enum.drop(bind, checkfirst=True)
