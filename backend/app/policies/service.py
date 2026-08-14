from datetime import date
from uuid import UUID
from zoneinfo import ZoneInfo

AGE_BANDS = ("YOUNG_CHILD", "PRETEEN", "TEEN", "OLDER_TEEN")


def age_on(birth: date, today: date) -> int:
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def age_band_for_dob(birth: date, today: date | None = None) -> str:
    age = age_on(birth, today or date.today())
    if 5 <= age <= 8:
        return "YOUNG_CHILD"
    if 9 <= age <= 12:
        return "PRETEEN"
    if 13 <= age <= 15:
        return "TEEN"
    if 16 <= age <= 17:
        return "OLDER_TEEN"
    raise ValueError("Child age must be between 5 and 17")


def validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except Exception as exc:
        raise ValueError("timezone must be a valid IANA timezone") from exc
    return value


def default_policy(family_id: UUID, child_id: UUID, band: str, timezone: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "policy_version": 1,
        "family_id": str(family_id),
        "child_profile_id": str(child_id),
        "issued_at": "1970-01-01T00:00:00Z",
        "expires_soft_at": "9999-12-31T23:59:59Z",
        "age_band": band,
        "base_policy": {
            "timezone": timezone,
            "unknown_domain_policy": "BLOCK_WHILE_CLASSIFYING",
            "unknown_app_policy": "LIMIT_AND_NOTIFY"
            if band in {"YOUNG_CHILD", "PRETEEN"}
            else "ALLOW_AND_NOTIFY",
            "unknown_app_daily_minutes": 30 if band in {"YOUNG_CHILD", "PRETEEN"} else None,
            "hard_category_rules": [],
            "default_category_rules": [],
            "safety_allowlist": [],
        },
        "app_rules": [],
        "domain_rules": [],
        "category_rules": [],
        "routines": [],
        "temporary_overrides": [],
        "communication_safety": {"enabled": True},
        "signature": "",
    }
