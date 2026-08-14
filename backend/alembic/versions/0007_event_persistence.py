"""persist minimized device events"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007_event_persistence"
down_revision = "0006_guardian_invitations"
branch_labels = None
depends_on = None


def _common_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    ]


def upgrade() -> None:
    for table, extra in (
        (
            "safety_events",
            [
                sa.Column("app_ref", sa.String(length=200)),
                sa.Column("domain", sa.String(length=253)),
            ],
        ),
        (
            "web_events",
            [
                sa.Column("domain", sa.String(length=253)),
                sa.Column("app_ref", sa.String(length=200)),
            ],
        ),
        (
            "usage_aggregates",
            [
                sa.Column("app_ref", sa.String(length=200)),
                sa.Column("category", sa.String(length=50)),
                sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
            ],
        ),
    ):
        op.create_table(table, *_common_columns()[:4], *extra, *_common_columns()[4:])
        op.create_index(f"ix_{table}_device_id", table, ["device_id"])
    op.create_table(
        "protection_health_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("protection_state", sa.String(length=30), nullable=False),
        sa.Column("capabilities", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_protection_health_events_device_id",
        "protection_health_events",
        ["device_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_protection_health_events_device_id", table_name="protection_health_events")
    op.drop_table("protection_health_events")
    for table in ("usage_aggregates", "web_events", "safety_events"):
        op.drop_index(f"ix_{table}_device_id", table_name=table)
        op.drop_table(table)
