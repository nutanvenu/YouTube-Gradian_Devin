from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GuardianRole(StrEnum):
    OWNER = "OWNER"
    CO_GUARDIAN = "CO_GUARDIAN"


class Parent(TimestampMixin, Base):
    __tablename__ = "parents"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    guardianships: Mapped[list["FamilyGuardian"]] = relationship(back_populates="parent")


class Family(TimestampMixin, Base):
    __tablename__ = "families"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    guardians: Mapped[list["FamilyGuardian"]] = relationship(
        back_populates="family", cascade="all, delete-orphan"
    )
    children: Mapped[list["ChildProfile"]] = relationship(
        back_populates="family", cascade="all, delete-orphan"
    )


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
    family: Mapped[Family] = relationship(back_populates="guardians")
    parent: Mapped[Parent] = relationship(back_populates="guardianships")


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
    family: Mapped[Family] = relationship(back_populates="children")


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


class RefreshToken(TimestampMixin, Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    parent_id: Mapped[UUID] = mapped_column(
        ForeignKey("parents.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class DeviceCredential(TimestampMixin, Base):
    __tablename__ = "device_credentials"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), unique=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
