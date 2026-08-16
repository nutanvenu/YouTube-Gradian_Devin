"""store current daily cumulative usage snapshots

Revision ID: 0020_usage_daily_snapshots
Revises: 0019_comm_signal_meta
"""

import sqlalchemy as sa

from alembic import op

revision = "0020_usage_daily_snapshots"
down_revision = "0019_comm_signal_meta"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usage_aggregates", sa.Column("snapshot_day", sa.Date(), nullable=True))
    op.add_column(
        "usage_aggregates", sa.Column("snapshot_key", sa.String(length=255), nullable=True)
    )
    # Preserve existing reportability while making legacy rows participate in the
    # same latest-snapshot semantics. Their saved timezone is authoritative.
    op.execute(
        """
        UPDATE usage_aggregates
        SET snapshot_day = (occurred_at AT TIME ZONE timezone)::date,
            snapshot_key = CASE
              WHEN app_ref IS NOT NULL THEN 'APP:' || app_ref
              WHEN category IS NOT NULL THEN 'CATEGORY:' || category
              ELSE 'DEVICE'
            END
        """
    )
    op.execute(
        """
        WITH ranked AS (
          SELECT id,
                 row_number() OVER (
                   PARTITION BY device_id, snapshot_day, snapshot_key
                   ORDER BY occurred_at DESC, created_at DESC, id DESC
                 ) AS row_number
          FROM usage_aggregates
          WHERE snapshot_day IS NOT NULL AND snapshot_key IS NOT NULL
        )
        DELETE FROM usage_aggregates AS usage
        USING ranked
        WHERE usage.id = ranked.id AND ranked.row_number > 1
        """
    )
    op.create_index(
        "uq_usage_aggregates_daily_snapshot",
        "usage_aggregates",
        ["device_id", "snapshot_day", "snapshot_key"],
        unique=True,
        postgresql_where=sa.text("snapshot_day IS NOT NULL AND snapshot_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_usage_aggregates_daily_snapshot", table_name="usage_aggregates")
    op.drop_column("usage_aggregates", "snapshot_key")
    op.drop_column("usage_aggregates", "snapshot_day")
