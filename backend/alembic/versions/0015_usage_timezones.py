"""Persist the source timezone for usage events.

Revision ID: 0015_usage_timezones
Revises: 0014_reputation
"""

import sqlalchemy as sa

from alembic import op

revision = "0015_usage_timezones"
down_revision = "0014_reputation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usage_aggregates",
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
    )
    op.alter_column("usage_aggregates", "timezone", server_default=None)


def downgrade() -> None:
    op.drop_column("usage_aggregates", "timezone")
