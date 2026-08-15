"""persist idempotency results"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005_idempotency_records"
down_revision = "0004_refresh_token_family"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.String(length=60), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("operation", "idempotency_key"),
    )


def downgrade() -> None:
    op.drop_table("idempotency_records")
