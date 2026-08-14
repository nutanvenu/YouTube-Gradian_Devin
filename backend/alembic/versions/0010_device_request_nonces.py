"""device request proof replay protection

Revision ID: 0010_device_request_nonces
Revises: 0009_requests_push
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_device_request_nonces"
down_revision = "0009_requests_push"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "device_request_nonces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nonce", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "nonce"),
    )
    op.create_index("ix_device_request_nonces_device_id", "device_request_nonces", ["device_id"])


def downgrade() -> None:
    op.drop_index("ix_device_request_nonces_device_id", table_name="device_request_nonces")
    op.drop_table("device_request_nonces")
