"""one-time auth tokens"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003_auth_one_time_tokens"
down_revision = "0002_pairing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "one_time_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("parents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("purpose", sa.String(30), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("one_time_tokens")
