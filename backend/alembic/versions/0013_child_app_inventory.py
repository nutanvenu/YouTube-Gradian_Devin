"""persist child app inventory and review state"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0013_child_app_inventory"
down_revision = "0012_event_categories"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "child_app_inventory",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("child_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_app_id", sa.String(length=200), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["child_profile_id"], ["child_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_parent_id"], ["parents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("child_profile_id", "platform_app_id"),
    )
    op.create_index("ix_child_app_inventory_child", "child_app_inventory", ["child_profile_id"])


def downgrade() -> None:
    op.drop_index("ix_child_app_inventory_child", table_name="child_app_inventory")
    op.drop_table("child_app_inventory")
