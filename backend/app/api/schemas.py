from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ErrorBody(BaseModel):
    code: str
    message: str


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginIn(SignupIn):
    pass


class TokensOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=20)


class TokenRequestIn(BaseModel):
    email: EmailStr


class TokenConfirmIn(BaseModel):
    token: str = Field(min_length=20)


class PasswordResetConfirmIn(BaseModel):
    token: str = Field(min_length=20)
    password: str = Field(min_length=12)


class ParentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    email_verified_at: datetime | None


class FamilyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class FamilyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str


class ChildCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    date_of_birth: date
    timezone: str = Field(min_length=1, max_length=64)


class ChildUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    date_of_birth: date | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)


class ChildOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    family_id: UUID
    name: str
    date_of_birth: date
    age_band: str
    timezone: str
    policy_document: dict[str, object]


class GuardianOut(BaseModel):
    id: UUID
    parent_id: UUID
    family_id: UUID
    role: str


class PairingOut(BaseModel):
    session_id: UUID
    qr_payload: str
    expires_at: datetime


class PairingRedeemIn(BaseModel):
    session_id: UUID
    code: str = Field(pattern=r"^\d{6}$")
    child_profile_id: UUID
    platform: str = Field(min_length=1, max_length=30)
    public_key: str = Field(min_length=32)


class DeviceCredentialOut(BaseModel):
    device_id: UUID
    device_token: str
