from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.models import Base, TimestampMixin


class Device(TimestampMixin, Base):
    __tablename__ = "devices"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    child_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("child_profiles.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(30))
    public_key: Mapped[str] = mapped_column(Text)
    capabilities: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    protection_state: Mapped[str] = mapped_column(String(30), default="UNKNOWN")
    policy_version_applied: Mapped[int | None] = mapped_column(Integer)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeviceCredential(TimestampMixin, Base):
    __tablename__ = "device_credentials"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), unique=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
