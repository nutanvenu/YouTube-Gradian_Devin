import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Literal, cast
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

PASSWORD_WORDS = re.compile(r"\S+")
CAPABILITY_LEVELS = {"FULL", "LIMITED", "BEST_EFFORT", "UNAVAILABLE", "REGION_LIMITED"}
CAPABILITY_KEYS = {
    "app_usage",
    "app_blocking",
    "web_filtering",
    "communication_risk_signals",
    "vpn_filtering",
    "accessibility_signals",
    "notification_signals",
}
_CONTENT_RISK_CONTRACT_PATH = (
    Path(__file__).resolve().parents[3] / "packages" / "contracts" / "content-risk-contract.json"
)
_CONTENT_RISK_CONTRACT = json.loads(_CONTENT_RISK_CONTRACT_PATH.read_text())
RISK_SEVERITIES = tuple(_CONTENT_RISK_CONTRACT["severities"])
CONTENT_RISK_SOURCES = tuple(_CONTENT_RISK_CONTRACT["signal_sources"])
CONTENT_RISK_ACTIONS = tuple(_CONTENT_RISK_CONTRACT["actions"])
CONTENT_RISK_CATEGORIES = tuple(_CONTENT_RISK_CONTRACT["categories"])
CONTENT_RISK_REASON_CODES = frozenset(_CONTENT_RISK_CONTRACT["reason_codes"])
# Older local providers used policy-taxonomy labels below. Keep their minimized
# events readable, but persist one canonical content-risk taxonomy.
CONTENT_RISK_CATEGORY_ALIASES = cast(
    dict[str, str], dict(_CONTENT_RISK_CONTRACT["category_aliases"])
)


def normalize_content_risk_category(value: str) -> str:
    normalized = value.strip().upper()
    return CONTENT_RISK_CATEGORY_ALIASES.get(normalized, normalized)


def validate_content_reason_code(value: str) -> str:
    normalized = value.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*(?:\+[A-Z][A-Z0-9_]*)*", normalized):
        raise ValueError("Invalid content reason code")
    if any(component not in CONTENT_RISK_REASON_CODES for component in normalized.split("+")):
        raise ValueError("Unknown content reason code")
    return normalized


HOSTNAME = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)


def validate_iana_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except Exception as error:
        raise ValueError("Invalid IANA timezone") from error
    return value


IanaTimezone = Annotated[str, AfterValidator(validate_iana_timezone)]


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
    timezone: IanaTimezone = Field(min_length=1, max_length=64)


class ChildUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    date_of_birth: date | None = None
    timezone: IanaTimezone | None = Field(default=None, min_length=1, max_length=64)


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
    family_id: UUID


class DeviceAckIn(BaseModel):
    policy_version: int = Field(ge=1)


class CapabilityStatusIn(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    level: Literal["FULL", "LIMITED", "BEST_EFFORT", "UNAVAILABLE", "REGION_LIMITED"]
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
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "allOf": [
                {
                    "if": {
                        "properties": {"event_type": {"const": "SAFETY_CONTENT_RISK"}},
                        "required": ["event_type"],
                    },
                    "then": {
                        "required": [
                            "app_ref",
                            "category",
                            "severity",
                            "confidence",
                            "reason_code",
                            "signal_source",
                            "action",
                            "classifier_version",
                            "capability_level",
                            "content_fingerprint",
                        ]
                    },
                }
            ]
        },
    )

    event_type: str = Field(min_length=1, max_length=50)
    occurred_at: datetime
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    app_ref: str | None = Field(
        default=None, max_length=200, pattern=r"^[A-Za-z0-9._-]+$"
    )
    domain: str | None = Field(default=None, max_length=253)
    category: str | None = Field(default=None, max_length=50)
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason_code: str | None = Field(default=None, min_length=1, max_length=100)
    signal_source: Literal[
        "NOTIFICATION",
        "ACCESSIBILITY_TEXT",
        "NETWORK_DESTINATION",
        "USAGE",
        "MEDIA_METADATA",
    ] | None = None
    action: Literal["ALLOW", "WARN", "BLOCK_AND_REQUEST"] | None = None
    classifier_version: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9._-]*$",
    )
    capability_level: Literal[
        "FULL", "LIMITED", "BEST_EFFORT", "UNAVAILABLE", "REGION_LIMITED"
    ] | None = None
    content_fingerprint: str | None = Field(
        default=None, pattern=r"^[a-f0-9]{64}$"
    )
    public_content_ref: "PublicContentReferenceIn | None" = None
    duration_seconds: int = Field(default=0, ge=0, le=86400)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except Exception as error:
                raise ValueError("Invalid IANA timezone") from error
        return value

    @field_validator("category")
    @classmethod
    def normalize_event_category(cls, value: str | None) -> str | None:
        # Event categories are intentionally additive: web/app policy categories
        # remain valid while legacy content-risk aliases become canonical.
        return normalize_content_risk_category(value) if value is not None else None

    @field_validator("domain")
    @classmethod
    def normalize_domain(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower().rstrip(".")
        if not HOSTNAME.fullmatch(normalized):
            raise ValueError("Domain must be a hostname without a URL, path, or query")
        return normalized

    @model_validator(mode="after")
    def require_content_risk_verdict(self) -> "MinimizedEvent":
        if self.event_type.upper() != "SAFETY_CONTENT_RISK":
            return self
        if not self.app_ref:
            raise ValueError("SAFETY_CONTENT_RISK requires app_ref")
        if self.category not in CONTENT_RISK_CATEGORIES:
            raise ValueError("SAFETY_CONTENT_RISK requires a canonical category")
        if self.severity is None or self.confidence is None:
            raise ValueError("SAFETY_CONTENT_RISK requires severity and confidence")
        if self.signal_source is None or self.action is None:
            raise ValueError("SAFETY_CONTENT_RISK requires signal source and action")
        if self.classifier_version is None or self.capability_level is None:
            raise ValueError("SAFETY_CONTENT_RISK requires classifier and capability")
        if self.content_fingerprint is None:
            raise ValueError("SAFETY_CONTENT_RISK requires a keyed fingerprint")
        if self.reason_code is None:
            raise ValueError("SAFETY_CONTENT_RISK requires a canonical reason code")
        self.reason_code = validate_content_reason_code(self.reason_code)
        return self


class EventBatchIn(BaseModel):
    events: list[MinimizedEvent] = Field(min_length=1, max_length=100)


class ObservedAppIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform_app_id: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=50)
    observed_at: datetime


class ObservedAppBatchIn(BaseModel):
    apps: list[ObservedAppIn] = Field(max_length=500)


class ObservedAppOut(BaseModel):
    platform_app_id: str
    display_name: str
    category: str | None
    observed_at: datetime
    reviewed: bool


class ActivityEventOut(BaseModel):
    id: UUID
    kind: Literal["WEB", "SAFETY"]
    event_type: str
    occurred_at: datetime
    domain: str | None
    app_ref: str | None
    category: str | None
    severity: str | None
    confidence: float | None
    reason_code: str | None


class ActivityUsagePointOut(BaseModel):
    app_ref: str | None
    category: str | None
    duration_seconds: int
    event_type: str
    occurred_at: datetime


class UsageReportOut(BaseModel):
    child_profile_id: UUID
    period_start: date
    period_end: date
    timezone: str
    duration_seconds: int
    event_count: int
    by_app: dict[str, int]
    by_category: dict[str, int]
    unattributed_seconds: int = 0
    coverage: Literal["COMPLETE", "PARTIAL"] = "COMPLETE"


class PublicContentReferenceIn(BaseModel):
    """A public provider identifier, never a URL, query, title, or raw content."""

    model_config = ConfigDict(extra="forbid")

    provider: Literal["YOUTUBE", "INSTAGRAM", "X", "WEB"]
    content_id: str = Field(
        min_length=1,
        max_length=200,
        pattern=r"^[A-Za-z0-9._:-]+$",
    )


class ContentReviewEvidenceIn(BaseModel):
    """The sole server-visible representation of a locally classified item."""

    model_config = ConfigDict(extra="forbid")

    app_ref: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._-]+$")
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    category: Literal[
        "ADULT_NUDITY",
        "SEXUAL_CONTENT",
        "GROOMING_RISK",
        "BULLYING_HARASSMENT",
        "HATE_EXTREMISM",
        "SELF_HARM_SUICIDE",
        "GRAPHIC_VIOLENCE",
        "VIOLENCE",
        "DRUGS",
        "ALCOHOL_TOBACCO",
        "GAMBLING",
        "WEAPONS",
        "DANGEROUS_CHALLENGE",
        "ANONYMOUS_CHAT",
        "SCAM_FRAUD",
        "MALWARE_PHISHING",
        "STRONG_LANGUAGE",
        "AGE_INAPPROPRIATE",
        "PARENT_CUSTOM_RULE",
        "UNKNOWN",
    ]
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    confidence: float = Field(ge=0, le=1)
    reason_code: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Z][A-Z0-9_]*(?:\+[A-Z][A-Z0-9_]*)*$",
    )
    public_content_ref: PublicContentReferenceIn | None = None

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: object) -> object:
        return normalize_content_risk_category(value) if isinstance(value, str) else value

    @field_validator("reason_code")
    @classmethod
    def require_known_reason_code(cls, value: str) -> str:
        return validate_content_reason_code(value)


class RequestCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_type: Literal["MORE_TIME", "UNBLOCK_APP", "UNBLOCK_SITE", "CONTENT_REVIEW"]
    subject: str | None = Field(default=None, max_length=255)
    reason: str | None = Field(default=None, max_length=1000)
    content_review: ContentReviewEvidenceIn | None = None

    @model_validator(mode="after")
    def validate_content_review_shape(self) -> "RequestCreateIn":
        if self.request_type == "CONTENT_REVIEW":
            if self.content_review is None:
                raise ValueError("CONTENT_REVIEW requires minimized content_review evidence")
            if self.subject is not None or self.reason is not None:
                raise ValueError("CONTENT_REVIEW does not accept subject or free-form reason")
        elif self.content_review is not None:
            raise ValueError("content_review is only valid for CONTENT_REVIEW")
        return self


class RequestDecisionIn(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class RequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    child_profile_id: UUID
    device_id: UUID
    request_type: str
    subject: str | None
    state: str
    reason: str | None
    decision_reason: str | None
    expires_at: datetime | None
    content_review: ContentReviewEvidenceIn | None = None


class ContentApprovalOut(BaseModel):
    device_id: UUID
    app_ref: str
    fingerprint: str
    expires_at: datetime


class PushTokenIn(BaseModel):
    platform: Literal["ANDROID", "IOS", "WEB"]
    token: str = Field(min_length=20, max_length=4096)


class PushActionIn(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class PolicyMutationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal[
        "APP_ALLOW",
        "APP_BLOCK",
        "APP_UNLIMITED",
        "APP_DAILY_MINUTES",
        "APP_SCHEDULE",
        "DOMAIN_ALLOW",
        "DOMAIN_BLOCK",
        "CATEGORY_DAILY_MINUTES",
        "WEB_CATEGORY_ALLOW",
        "WEB_CATEGORY_BLOCK",
        "UNKNOWN_DOMAIN_POLICY",
        "UNKNOWN_APP_POLICY",
        "ROUTINE_CREATE",
        "ROUTINE_UPDATE",
        "ROUTINE_DELETE",
        "ROUTINE_ACTIVATE",
        "ROUTINE_DEACTIVATE",
        "COMMUNICATION_SENSITIVITY",
        "COMMUNICATION_ENABLED",
        "CONTENT_BLOCK_THRESHOLD",
        "TEMPORARY_EXCEPTION",
        "TEMPORARY_SCREEN_TIME",
        "PAUSE_INTERNET",
        "RESUME_INTERNET",
    ]
    target: str = Field(min_length=1, max_length=512)
    value: str | int | dict[str, object] | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_content_block_threshold(self) -> "PolicyMutationIn":
        if self.operation != "CONTENT_BLOCK_THRESHOLD":
            return self
        if self.target != "content_safety":
            raise ValueError("Content block threshold target must be content_safety")
        if self.value not in RISK_SEVERITIES:
            raise ValueError("Invalid content block threshold")
        return self
