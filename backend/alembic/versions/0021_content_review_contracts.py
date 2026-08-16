"""add minimized content-review and content-risk event contracts

Revision ID: 0021_content_review_contracts
Revises: 0020_usage_daily_snapshots
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0021_content_review_contracts"
down_revision = "0020_usage_daily_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("requests", sa.Column("content_app_ref", sa.String(length=200), nullable=True))
    op.add_column("requests", sa.Column("content_fingerprint", sa.String(length=64), nullable=True))
    op.add_column("requests", sa.Column("content_review", postgresql.JSONB(), nullable=True))
    op.create_check_constraint(
        "ck_requests_content_review_shape",
        "requests",
        """
        (
            request_type = 'CONTENT_REVIEW'
            AND subject IS NULL
            AND reason IS NULL
            AND content_app_ref ~ '^[A-Za-z0-9._-]+$'
            AND content_fingerprint ~ '^[a-f0-9]{64}$'
            AND jsonb_typeof(content_review) = 'object'
            AND content_review->>'app_ref' = content_app_ref
            AND content_review->>'fingerprint' = content_fingerprint
            AND content_review ?& ARRAY['app_ref', 'fingerprint', 'category', 'severity', 'confidence', 'reason_code']
            AND (content_review - 'app_ref' - 'fingerprint' - 'category' - 'severity' - 'confidence' - 'reason_code' - 'public_content_ref') = '{}'::jsonb
        )
        OR (
            request_type <> 'CONTENT_REVIEW'
            AND content_app_ref IS NULL
            AND content_fingerprint IS NULL
            AND (content_review IS NULL OR content_review = 'null'::jsonb)
        )
        """,
    )
    op.create_index(
        "ix_requests_pending_content_tuple",
        "requests",
        ["device_id", "content_app_ref", "content_fingerprint"],
        postgresql_where=sa.text(
            "request_type = 'CONTENT_REVIEW' AND state = 'PENDING' "
            "AND content_app_ref IS NOT NULL AND content_fingerprint IS NOT NULL"
        ),
    )
    op.create_table(
        "content_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("app_ref", sa.String(length=200), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "app_ref ~ '^[A-Za-z0-9._-]+$' AND fingerprint ~ '^[a-f0-9]{64}$'",
            name="ck_content_approvals_exact_tuple",
        ),
    )
    op.create_index("ix_content_approvals_device_id", "content_approvals", ["device_id"])
    op.create_index(
        "ix_content_approvals_device_expiry",
        "content_approvals",
        ["device_id", "expires_at"],
    )
    for name, column in (
        ("signal_source", sa.String(length=30)),
        ("action", sa.String(length=30)),
        ("classifier_version", sa.String(length=64)),
        ("capability_level", sa.String(length=30)),
        ("content_fingerprint", sa.String(length=64)),
        ("public_content_ref", postgresql.JSONB()),
    ):
        op.add_column("safety_events", sa.Column(name, column, nullable=True))


def downgrade() -> None:
    for name in (
        "public_content_ref",
        "content_fingerprint",
        "capability_level",
        "classifier_version",
        "action",
        "signal_source",
    ):
        op.drop_column("safety_events", name)
    op.drop_index("ix_content_approvals_device_expiry", table_name="content_approvals")
    op.drop_index("ix_content_approvals_device_id", table_name="content_approvals")
    op.drop_table("content_approvals")
    op.drop_index("ix_requests_pending_content_tuple", table_name="requests")
    op.drop_constraint("ck_requests_content_review_shape", "requests", type_="check")
    op.drop_column("requests", "content_review")
    op.drop_column("requests", "content_fingerprint")
    op.drop_column("requests", "content_app_ref")
