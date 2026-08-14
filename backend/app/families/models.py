from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.models import Base, TimestampMixin


class GuardianRole(StrEnum):
    OWNER = "OWNER"
    CO_GUARDIAN = "CO_GUARDIAN"


class Family(TimestampMixin, Base):
    __tablename__ = "families"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))


class FamilyGuardian(TimestampMixin, Base):
    __tablename__ = "family_guardians"
    __table_args__ = (UniqueConstraint("family_id", "parent_id"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    family_id: Mapped[UUID] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[UUID] = mapped_column(
        ForeignKey("parents.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(30))
