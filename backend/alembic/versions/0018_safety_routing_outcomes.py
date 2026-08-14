"""Persist every safety notification routing outcome."""

from collections.abc import Sequence

from alembic import op

revision: str = "0018_safety_routing_outcomes"
down_revision: str | None = "0017_communication_safety"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "safety_notifications_parent_id_dedupe_key_key",
        "safety_notifications",
        type_="unique",
    )
    op.create_index(
        "ix_safety_notifications_parent_dedupe",
        "safety_notifications",
        ["parent_id", "dedupe_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_safety_notifications_parent_dedupe", table_name="safety_notifications")
    op.create_unique_constraint(
        "safety_notifications_parent_id_dedupe_key_key",
        "safety_notifications",
        ["parent_id", "dedupe_key"],
    )
