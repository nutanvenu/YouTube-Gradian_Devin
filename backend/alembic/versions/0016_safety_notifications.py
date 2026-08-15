"""Persist safety notification routing decisions.

Revision ID: 0016_safety_notifications
Revises: 0015_usage_timezones
"""

import sqlalchemy as sa

from alembic import op

revision = "0016_safety_notifications"
down_revision = "0015_usage_timezones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "safety_notifications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=False),
        sa.Column("child_profile_id", sa.UUID(), nullable=False),
        sa.Column("safety_event_id", sa.UUID(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["parent_id"], ["parents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["child_profile_id"], ["child_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["safety_event_id"], ["safety_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_id", "dedupe_key"),
    )
    op.create_index(
        "ix_safety_notifications_parent_created",
        "safety_notifications",
        ["parent_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("safety_notifications")
