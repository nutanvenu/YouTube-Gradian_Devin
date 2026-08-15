"""add guardian invitations"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006_guardian_invitations"
down_revision = "0005_idempotency_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guardian_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_guardian_invitations_family_id", "guardian_invitations", ["family_id"]
    )
    op.create_index("ix_guardian_invitations_email", "guardian_invitations", ["email"])


def downgrade() -> None:
    op.drop_index("ix_guardian_invitations_email", table_name="guardian_invitations")
    op.drop_index("ix_guardian_invitations_family_id", table_name="guardian_invitations")
    op.drop_table("guardian_invitations")
