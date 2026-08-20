from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint
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


class ChildAppInventory(TimestampMixin, Base):
    __tablename__ = "child_app_inventory"
    __table_args__ = (
        UniqueConstraint("child_profile_id", "platform_app_id"),
        Index("ix_child_app_inventory_child", "child_profile_id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    child_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("child_profiles.id", ondelete="CASCADE"), index=True
    )
    platform_app_id: Mapped[str] = mapped_column(String(200))
    display_name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(50))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # This remains an explicitly partial, source-tagged observation.  It is not
    # an installed-package enumeration and deliberately contains no icon or
    # content payload.
    version_name: Mapped[str | None] = mapped_column(String(200))
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    installation_state: Mapped[str | None] = mapped_column(String(64))
    capability_sources: Mapped[list[str] | None] = mapped_column(JSONB)
    inventory_completeness: Mapped[str | None] = mapped_column(String(20))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("parents.id", ondelete="SET NULL")
    )
