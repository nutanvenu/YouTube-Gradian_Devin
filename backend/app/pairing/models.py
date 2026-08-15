from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.models import Base, TimestampMixin


class PairingSession(TimestampMixin, Base):
    __tablename__ = "pairing_sessions"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    child_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("child_profiles.id", ondelete="CASCADE"), index=True
    )
    code_hash: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
