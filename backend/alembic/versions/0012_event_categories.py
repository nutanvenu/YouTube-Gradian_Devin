"""store event categories for activity reporting"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "0012_event_categories"
down_revision = "0011_push_actions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("web_events", "safety_events"):
        op.add_column(table, sa.Column("category", sa.String(length=50), nullable=True))


def downgrade() -> None:
    for table in ("safety_events", "web_events"):
        op.drop_column(table, "category")
