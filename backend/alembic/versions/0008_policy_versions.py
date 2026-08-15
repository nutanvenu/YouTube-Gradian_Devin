"""policy documents and immutable signed bundles

Revision ID: 0008_policy_versions
Revises: 0007_event_persistence
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0008_policy_versions"
down_revision = "0007_event_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("child_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_policy_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["child_profile_id"], ["child_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("child_profile_id"),
    )
    op.create_index(
        "ix_policy_documents_child_profile_id", "policy_documents", ["child_profile_id"]
    )
    op.create_table(
        "policy_bundles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("child_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("author_parent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("previous_value", postgresql.JSONB()),
        sa.Column("new_value", postgresql.JSONB(), nullable=False),
        sa.Column("key_id", sa.String(length=128), nullable=False),
        sa.Column("signature", sa.String(length=512), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["document_id"], ["policy_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["child_profile_id"], ["child_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_parent_id"], ["parents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("child_profile_id", "policy_version"),
    )
    op.create_index("ix_policy_bundles_document_id", "policy_bundles", ["document_id"])
    op.create_index("ix_policy_bundles_child_profile_id", "policy_bundles", ["child_profile_id"])
    op.create_index(
        "uq_policy_bundle_current",
        "policy_bundles",
        ["child_profile_id"],
        unique=True,
        postgresql_where=sa.text("is_current IS TRUE"),
    )


def downgrade() -> None:
    op.drop_index("uq_policy_bundle_current", table_name="policy_bundles")
    op.drop_index("ix_policy_bundles_child_profile_id", table_name="policy_bundles")
    op.drop_index("ix_policy_bundles_document_id", table_name="policy_bundles")
    op.drop_table("policy_bundles")
    op.drop_index("ix_policy_documents_child_profile_id", table_name="policy_documents")
    op.drop_table("policy_documents")
