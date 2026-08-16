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

BACKFILL_USAGE_SNAPSHOTS_SQL = """
UPDATE usage_aggregates AS usage
SET snapshot_day = (usage.occurred_at AT TIME ZONE resolved.timezone_name)::date,
    snapshot_key = CASE
      WHEN usage.app_ref IS NOT NULL THEN 'APP:' || usage.app_ref
      WHEN usage.category IS NOT NULL THEN 'CATEGORY:' || usage.category
      ELSE 'DEVICE'
    END
FROM (
  SELECT legacy.id,
         COALESCE(valid_timezone.name, 'UTC') AS timezone_name
  FROM usage_aggregates AS legacy
  LEFT JOIN LATERAL (
    SELECT timezone.name
    FROM pg_timezone_names AS timezone
    WHERE timezone.name = legacy.timezone
    LIMIT 1
  ) AS valid_timezone ON TRUE
) AS resolved
WHERE usage.id = resolved.id
"""

# Keep the row with the latest timestamp/metadata, but retain the greatest
# cumulative value observed that day.  A delayed lower counter must never turn
# a historical 420-second day into 300 seconds during the migration.
DEDUPLICATE_USAGE_SNAPSHOTS_SQL = """
WITH ranked AS (
  SELECT id,
         max(duration_seconds) OVER (
           PARTITION BY device_id, snapshot_day, snapshot_key
         ) AS maximum_duration,
         row_number() OVER (
           PARTITION BY device_id, snapshot_day, snapshot_key
           ORDER BY occurred_at DESC, created_at DESC, id DESC
         ) AS row_number
  FROM usage_aggregates
  WHERE snapshot_day IS NOT NULL AND snapshot_key IS NOT NULL
)
UPDATE usage_aggregates AS usage
SET duration_seconds = ranked.maximum_duration
FROM ranked
WHERE usage.id = ranked.id AND ranked.row_number = 1
"""

DELETE_DUPLICATE_USAGE_SNAPSHOTS_SQL = """
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


def upgrade() -> None:
    op.add_column("usage_aggregates", sa.Column("snapshot_day", sa.Date(), nullable=True))
    op.add_column(
        "usage_aggregates", sa.Column("snapshot_key", sa.String(length=255), nullable=True)
    )
    # Preserve existing reportability while making legacy rows participate in the
    # same latest-snapshot semantics. Their saved timezone is authoritative.
    op.execute(BACKFILL_USAGE_SNAPSHOTS_SQL)
    op.execute(DEDUPLICATE_USAGE_SNAPSHOTS_SQL)
    op.execute(DELETE_DUPLICATE_USAGE_SNAPSHOTS_SQL)
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
