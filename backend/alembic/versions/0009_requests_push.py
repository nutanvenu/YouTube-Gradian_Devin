"""requests and push tokens

Revision ID: 0009_requests_push
Revises: 0008_policy_versions
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0009_requests_push"
down_revision = "0008_policy_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("child_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_type", sa.String(length=30), nullable=False),
        sa.Column("subject", sa.String(length=255)),
        sa.Column("state", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("reason", sa.Text()),
        sa.Column("decision_reason", sa.Text()),
        sa.Column("decided_by_parent_id", postgresql.UUID(as_uuid=True)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["child_profile_id"], ["child_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by_parent_id"], ["parents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_requests_child_profile_id", "requests", ["child_profile_id"])
    op.create_index("ix_requests_device_id", "requests", ["device_id"])
    op.create_index("ix_requests_child_state", "requests", ["child_profile_id", "state"])
    op.create_table(
        "push_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True)),
        sa.Column("device_id", postgresql.UUID(as_uuid=True)),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["parent_id"], ["parents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_id", "token_hash"),
    )


def downgrade() -> None:
    op.drop_table("push_tokens")
    op.drop_index("ix_requests_child_state", table_name="requests")
    op.drop_index("ix_requests_device_id", table_name="requests")
    op.drop_index("ix_requests_child_profile_id", table_name="requests")
    op.drop_table("requests")
