from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.models import Base, TimestampMixin


class SafetyEvent(TimestampMixin, Base):
    __tablename__ = "safety_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(50))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    app_ref: Mapped[str | None] = mapped_column(String(200))
    domain: Mapped[str | None] = mapped_column(String(253))
    category: Mapped[str | None] = mapped_column(String(50))
    severity: Mapped[str | None] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column()
    reason_code: Mapped[str | None] = mapped_column(String(100))
    signal_source: Mapped[str | None] = mapped_column(String(30))
    action: Mapped[str | None] = mapped_column(String(30))
    classifier_version: Mapped[str | None] = mapped_column(String(64))
    capability_level: Mapped[str | None] = mapped_column(String(30))
    content_fingerprint: Mapped[str | None] = mapped_column(String(64))
    public_content_ref: Mapped[dict[str, object] | None] = mapped_column(JSONB)


class WebEvent(TimestampMixin, Base):
    __tablename__ = "web_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(50))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    domain: Mapped[str | None] = mapped_column(String(253))
    app_ref: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(50))


class UsageAggregate(TimestampMixin, Base):
    __tablename__ = "usage_aggregates"
    __table_args__ = (
        Index(
            "uq_usage_aggregates_daily_snapshot",
            "device_id",
            "snapshot_day",
            "snapshot_key",
            unique=True,
            postgresql_where=text("snapshot_day IS NOT NULL AND snapshot_key IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(50))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    app_ref: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(50))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    # New uploads are current cumulative values, not an event stream.  Older rows
    # remain readable during the additive migration, so these columns are nullable.
    snapshot_day: Mapped[date | None] = mapped_column(Date)
    snapshot_key: Mapped[str | None] = mapped_column(String(255))


class ProtectionHealthEvent(TimestampMixin, Base):
    __tablename__ = "protection_health_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    protection_state: Mapped[str] = mapped_column(String(30))
    capabilities: Mapped[dict[str, object]] = mapped_column(JSONB)


class SafetyNotification(TimestampMixin, Base):
    __tablename__ = "safety_notifications"
    __table_args__ = (
        Index("ix_safety_notifications_parent_created", "parent_id", "created_at"),
        Index("ix_safety_notifications_parent_dedupe", "parent_id", "dedupe_key"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    parent_id: Mapped[UUID] = mapped_column(ForeignKey("parents.id", ondelete="CASCADE"))
    child_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("child_profiles.id", ondelete="CASCADE"), index=True
    )
    safety_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("safety_events.id", ondelete="CASCADE"), index=True
    )
    dedupe_key: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
