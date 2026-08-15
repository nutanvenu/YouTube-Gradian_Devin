"""push notification action tokens

Revision ID: 0011_push_actions
Revises: 0010_device_request_nonces
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0011_push_actions"
down_revision = "0010_device_request_nonces"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "push_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["parents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_push_actions_request_id", "push_actions", ["request_id"])
    op.create_index("ix_push_actions_parent_id", "push_actions", ["parent_id"])
    op.create_index(
        "ix_push_actions_request_parent", "push_actions", ["request_id", "parent_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_push_actions_request_parent", table_name="push_actions")
    op.drop_index("ix_push_actions_parent_id", table_name="push_actions")
    op.drop_index("ix_push_actions_request_id", table_name="push_actions")
    op.drop_table("push_actions")
