from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.models import Base, TimestampMixin


class RequestState(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class RequestType(StrEnum):
    MORE_TIME = "MORE_TIME"
    UNBLOCK_APP = "UNBLOCK_APP"
    UNBLOCK_SITE = "UNBLOCK_SITE"


class Request(TimestampMixin, Base):
    __tablename__ = "requests"
    __table_args__ = (Index("ix_requests_child_state", "child_profile_id", "state"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    child_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("child_profiles.id", ondelete="CASCADE"), index=True
    )
    device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), index=True
    )
    request_type: Mapped[str] = mapped_column(String(30))
    subject: Mapped[str | None] = mapped_column(String(255))
    state: Mapped[str] = mapped_column(String(20), default=RequestState.PENDING.value)
    reason: Mapped[str | None] = mapped_column(Text)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    decided_by_parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("parents.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
