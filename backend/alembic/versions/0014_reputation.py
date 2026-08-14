"""add signed reputation state"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014_reputation"
down_revision = "0013_child_app_inventory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reputation_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "reputation_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_kind", sa.String(length=20), nullable=False),
        sa.Column("identifier", sa.String(length=253), nullable=False),
        sa.Column("verdict", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("rationale", sa.String(length=500), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bundle_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("target_kind", "identifier"),
    )
    op.create_index("ix_reputation_entries_identifier", "reputation_entries", ["identifier"])
    op.create_table(
        "reputation_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_version", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("base_version", sa.Integer(), nullable=True),
        sa.Column("bundle", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bundle_version"),
    )


def downgrade() -> None:
    op.drop_table("reputation_revisions")
    op.drop_index("ix_reputation_entries_identifier", table_name="reputation_entries")
    op.drop_table("reputation_entries")
    op.drop_table("reputation_state")
