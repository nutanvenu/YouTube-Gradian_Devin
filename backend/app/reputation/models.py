from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.models import Base, TimestampMixin


class ReputationState(TimestampMixin, Base):
    __tablename__ = "reputation_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    current_version: Mapped[int] = mapped_column(Integer, default=0)


class ReputationEntry(TimestampMixin, Base):
    __tablename__ = "reputation_entries"
    __table_args__ = (
        UniqueConstraint("target_kind", "identifier"),
        Index("ix_reputation_entries_identifier", "identifier"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    target_kind: Mapped[str] = mapped_column(String(20))
    identifier: Mapped[str] = mapped_column(String(253))
    verdict: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(200))
    rationale: Mapped[str] = mapped_column(String(500))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    bundle_version: Mapped[int] = mapped_column(Integer)


class ReputationRevision(TimestampMixin, Base):
    __tablename__ = "reputation_revisions"
    __table_args__ = (UniqueConstraint("bundle_version"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    bundle_version: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(10))
    base_version: Mapped[int | None] = mapped_column(Integer)
    bundle: Mapped[dict[str, object]] = mapped_column(JSONB)
