"""persist source-tagged partial inventory lifecycle metadata

Revision ID: 0022_inventory_lifecycle_metadata
Revises: 0021_content_review_contracts
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0022_inventory_lifecycle_metadata"
down_revision = "0021_content_review_contracts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("child_app_inventory", sa.Column("version_name", sa.String(length=200), nullable=True))
    op.add_column("child_app_inventory", sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("child_app_inventory", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("child_app_inventory", sa.Column("installation_state", sa.String(length=64), nullable=True))
    op.add_column("child_app_inventory", sa.Column("capability_sources", postgresql.JSONB(), nullable=True))
    op.add_column("child_app_inventory", sa.Column("inventory_completeness", sa.String(length=20), nullable=True))


def downgrade() -> None:
    for column in (
        "inventory_completeness",
        "capability_sources",
        "installation_state",
        "last_seen_at",
        "first_seen_at",
        "version_name",
    ):
        op.drop_column("child_app_inventory", column)
