from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import Date, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.models import Base, TimestampMixin


class ChildProfile(TimestampMixin, Base):
    __tablename__ = "child_profiles"
    __table_args__ = (UniqueConstraint("family_id", "name"), Index("ix_child_family", "family_id"))
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    family_id: Mapped[UUID] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    date_of_birth: Mapped[date] = mapped_column(Date)
    age_band: Mapped[str] = mapped_column(String(30))
    timezone: Mapped[str] = mapped_column(String(64))
    policy_document: Mapped[dict[str, object]] = mapped_column(JSONB)
