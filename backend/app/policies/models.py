from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.models import Base, TimestampMixin


class PolicyDocument(TimestampMixin, Base):
    __tablename__ = "policy_documents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    child_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("child_profiles.id", ondelete="CASCADE"), unique=True, index=True
    )
    current_policy_version: Mapped[int] = mapped_column(Integer, default=0)


class PolicyBundle(TimestampMixin, Base):
    __tablename__ = "policy_bundles"
    __table_args__ = (
        UniqueConstraint("child_profile_id", "policy_version"),
        Index(
            "uq_policy_bundle_current",
            "child_profile_id",
            unique=True,
            postgresql_where=text("is_current IS TRUE"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("policy_documents.id", ondelete="CASCADE"), index=True
    )
    child_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("child_profiles.id", ondelete="CASCADE"), index=True
    )
    policy_version: Mapped[int] = mapped_column(Integer)
    author_parent_id: Mapped[UUID] = mapped_column(ForeignKey("parents.id"))
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    previous_value: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    new_value: Mapped[dict[str, object]] = mapped_column(JSONB)
    key_id: Mapped[str] = mapped_column(String(128))
    signature: Mapped[str] = mapped_column(String(512))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
