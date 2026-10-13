"""Live YouTube pause and structured exact-video review details.

Revision ID: 0024_video_live_controls
Revises: 0023_video_settings
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0024_video_live_controls"
down_revision = "0023_video_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "child_video_settings",
        sa.Column("youtube_paused", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("requests", sa.Column("video_review", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("requests", "video_review")
    op.drop_column("child_video_settings", "youtube_paused")
