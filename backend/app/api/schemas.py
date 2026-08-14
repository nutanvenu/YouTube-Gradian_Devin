import re
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

PASSWORD_WORDS = re.compile(r"\S+")
CAPABILITY_LEVELS = {"FULL", "BEST_EFFORT", "UNAVAILABLE", "REGION_LIMITED"}
CAPABILITY_KEYS = {
    "app_usage",
    "app_blocking",
    "web_filtering",
    "communication_risk_signals",
    "vpn_filtering",
    "accessibility_signals",
    "notification_signals",
}


class ErrorBody(BaseModel):
    code: str
    message: str


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


def validate_password_strength(value: str) -> str:
    classes = sum(
        (
            any(character.islower() for character in value),
            any(character.isupper() for character in value),
            any(character.isdigit() for character in value),
            any(not character.isalnum() and not character.isspace() for character in value),
        )
    )
    if classes < 3 and len(PASSWORD_WORDS.findall(value)) < 4:
        raise ValueError("Password must use at least three character classes or four words")
    return value


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


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
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


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


class GuardianInviteIn(BaseModel):
    email: EmailStr


class GuardianAcceptIn(BaseModel):
    token: str = Field(min_length=20)


class PairingOut(BaseModel):
    session_id: UUID
    code: str = Field(pattern=r"^\d{6}$")
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


class DeviceAckIn(BaseModel):
    policy_version: int = Field(ge=1)


class CapabilityStatusIn(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    level: Literal["FULL", "BEST_EFFORT", "UNAVAILABLE", "REGION_LIMITED"]
    detail: str | None = None
    updated_at: datetime = Field(alias="updatedAt")


class DeviceHeartbeatIn(BaseModel):
    protection_state: Literal["HEALTHY", "DEGRADED", "DISABLED", "UNKNOWN"]
    capabilities: dict[str, "CapabilityStatusIn"] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_capability_keys(self) -> "DeviceHeartbeatIn":
        unknown = set(self.capabilities) - CAPABILITY_KEYS
        if unknown:
            raise ValueError("Unknown capability key")
        return self


class MinimizedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=1, max_length=50)
    occurred_at: datetime
    app_ref: str | None = Field(default=None, max_length=200)
    domain: str | None = Field(default=None, max_length=253)


class EventBatchIn(BaseModel):
    events: list[MinimizedEvent] = Field(min_length=1, max_length=100)
