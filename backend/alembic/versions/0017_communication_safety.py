"""Persist minimized communication-safety severity."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_communication_safety"
down_revision: str | None = "0016_safety_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("safety_events", sa.Column("severity", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("safety_events", "severity")
