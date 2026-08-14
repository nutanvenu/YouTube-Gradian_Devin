"""Persist communication-safety confidence and reason metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_comm_signal_meta"
down_revision: str | None = "0018_safety_routing_outcomes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("safety_events", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("safety_events", sa.Column("reason_code", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("safety_events", "reason_code")
    op.drop_column("safety_events", "confidence")
