from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.models import Base, TimestampMixin


class PushToken(TimestampMixin, Base):
    __tablename__ = "push_tokens"
    __table_args__ = (UniqueConstraint("parent_id", "token_hash"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("parents.id", ondelete="CASCADE"))
    device_id: Mapped[UUID | None] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(128))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PushAction(TimestampMixin, Base):
    __tablename__ = "push_actions"
    __table_args__ = (
        UniqueConstraint("token_hash"),
        Index("ix_push_actions_request_parent", "request_id", "parent_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[UUID] = mapped_column(
        ForeignKey("parents.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
