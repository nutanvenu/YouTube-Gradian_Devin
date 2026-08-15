"""identity, family, child, and device tables"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001_identity_devices"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    now = sa.func.now()
    op.create_table(
        "parents",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_table(
        "families",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_table(
        "family_guardians",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "family_id", uuid, sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "parent_id", uuid, sa.ForeignKey("parents.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.UniqueConstraint("family_id", "parent_id"),
    )
    op.create_table(
        "child_profiles",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "family_id", uuid, sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("age_band", sa.String(30), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("policy_document", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.UniqueConstraint("family_id", "name"),
    )
    op.create_table(
        "devices",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "child_profile_id",
            uuid,
            sa.ForeignKey("child_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(30), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("capabilities", postgresql.JSONB(), nullable=False),
        sa.Column("protection_state", sa.String(30), nullable=False),
        sa.Column("policy_version_applied", sa.Integer()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "parent_id", uuid, sa.ForeignKey("parents.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("replaced_by_id", uuid),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_table(
        "device_credentials",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "device_id",
            uuid,
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )


def downgrade() -> None:
    for name in (
        "device_credentials",
        "refresh_tokens",
        "devices",
        "child_profiles",
        "family_guardians",
        "families",
        "parents",
    ):
        op.drop_table(name)
