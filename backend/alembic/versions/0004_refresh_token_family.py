"""group refresh tokens into rotation families"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004_refresh_token_family"
down_revision = "0003_auth_one_time_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "family_id")
