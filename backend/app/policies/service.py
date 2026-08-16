import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import PolicyBundle, PolicyDocument
from .signing import signer

AGE_BANDS = ("YOUNG_CHILD", "PRETEEN", "TEEN", "OLDER_TEEN")
_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "policy-schema"
    / "schema"
    / "policy-bundle.schema.json"
)
_HARD_CATEGORIES_PATH = (
    Path(__file__).resolve().parents[3] / "packages" / "contracts" / "hard-categories.json"
)


def _shared_hard_categories() -> tuple[str, ...]:
    values = tuple(json.loads(_HARD_CATEGORIES_PATH.read_text()))
    if not values or not all(isinstance(value, str) for value in values):
        raise RuntimeError("Shared HARD_CATEGORIES definition is empty")
    return values


HARD_CATEGORIES = _shared_hard_categories()


def _rule(rule_id: str, category: str, action: str, **values: object) -> dict[str, object]:
    return {"rule_id": rule_id, "category": category, "action": action, **values}


def _bedtime(band: str) -> dict[str, object]:
    windows = {
        "YOUNG_CHILD": ("20:00", "07:00"),
        "PRETEEN": ("21:00", "07:00"),
        "TEEN": ("22:00", "06:00"),
        "OLDER_TEEN": ("23:00", "06:00"),
    }
    start, end = windows[band]
    return {
        "routine_id": f"bedtime-{band.lower()}",
        "name": "Bedtime",
        "kind": "SCHEDULED",
        "window": {"days": [1, 2, 3, 4, 5, 6, 7], "start": start, "end": end},
        "blocked_categories": [
            "SOCIAL_MEDIA",
            "ANONYMOUS_CHAT",
            "DATING",
            "STREAMING_VIDEO",
            "GAMES",
            "MESSAGING",
        ],
        "web_mode": "STRICT",
        "communication_mode": "ESSENTIAL_ONLY",
    }


def _band_rules(
    band: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]], int, str, str, int | None]:
    hard = [
        _rule(f"hard-{category.lower()}", category, "BLOCK", exclude_from_budget=True)
        for category in HARD_CATEGORIES
    ]
    common = {
        "YOUNG_CHILD": [
            _rule("default-anonymous-chat", "ANONYMOUS_CHAT", "BLOCK"),
            _rule("default-dating", "DATING", "BLOCK"),
            _rule("default-social-media", "SOCIAL_MEDIA", "BLOCK"),
            _rule("default-messaging", "MESSAGING", "LIMIT", daily_minutes=60),
            _rule("default-streaming-video", "STREAMING_VIDEO", "LIMIT", daily_minutes=60),
            _rule("default-games", "GAMES", "LIMIT", daily_minutes=60),
        ],
        "PRETEEN": [
            _rule("default-anonymous-chat", "ANONYMOUS_CHAT", "ASK_PARENT"),
            _rule("default-dating", "DATING", "ASK_PARENT"),
            _rule("default-social-media", "SOCIAL_MEDIA", "ASK_PARENT"),
            _rule("default-messaging", "MESSAGING", "LIMIT", daily_minutes=120),
            _rule("default-streaming-video", "STREAMING_VIDEO", "LIMIT", daily_minutes=90),
            _rule("default-games", "GAMES", "LIMIT", daily_minutes=90),
        ],
        "TEEN": [
            _rule("default-anonymous-chat", "ANONYMOUS_CHAT", "ASK_PARENT"),
            _rule("default-dating", "DATING", "ASK_PARENT"),
            _rule("default-social-media", "SOCIAL_MEDIA", "LIMIT", daily_minutes=120),
            _rule("default-messaging", "MESSAGING", "LIMIT", daily_minutes=180),
            _rule("default-streaming-video", "STREAMING_VIDEO", "LIMIT", daily_minutes=120),
            _rule("default-games", "GAMES", "LIMIT", daily_minutes=120),
        ],
        "OLDER_TEEN": [
            _rule("default-anonymous-chat", "ANONYMOUS_CHAT", "ASK_PARENT"),
            _rule("default-dating", "DATING", "ASK_PARENT"),
            _rule("default-social-media", "SOCIAL_MEDIA", "LIMIT", daily_minutes=180),
            _rule("default-messaging", "MESSAGING", "LIMIT", daily_minutes=240),
            _rule("default-streaming-video", "STREAMING_VIDEO", "LIMIT", daily_minutes=180),
            _rule("default-games", "GAMES", "LIMIT", daily_minutes=180),
        ],
    }[band]
    values = {
        "YOUNG_CHILD": (120, "BLOCK_WHILE_CLASSIFYING", "LIMIT_AND_NOTIFY", 30),
        "PRETEEN": (180, "BLOCK_WHILE_CLASSIFYING", "LIMIT_AND_NOTIFY", 60),
        "TEEN": (240, "ALLOW_AND_NOTIFY", "ALLOW_AND_NOTIFY", None),
        "OLDER_TEEN": (300, "ALLOW_AND_NOTIFY", "ALLOW_AND_NOTIFY", None),
    }[band]
    return hard, common, values[0], values[1], values[2], values[3]


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


def default_policy(
    family_id: UUID,
    child_id: UUID,
    band: str,
    timezone: str,
    policy_version: int = 1,
) -> dict[str, object]:
    if band not in AGE_BANDS:
        raise ValueError(f"Unsupported age band: {band}")
    issued_at = datetime.now(UTC).replace(microsecond=0)
    hard, defaults, daily_budget, unknown_domain, unknown_app, unknown_app_minutes = _band_rules(
        band
    )
    base_policy: dict[str, object] = {
        "timezone": timezone,
        "unknown_domain_policy": unknown_domain,
        "unknown_app_policy": unknown_app,
        "daily_device_budget_minutes": daily_budget,
        "hard_category_rules": hard,
        "default_category_rules": defaults,
        "safety_allowlist": [],
    }
    if unknown_app_minutes is not None:
        base_policy["unknown_app_daily_minutes"] = unknown_app_minutes
    document: dict[str, object] = {
        "schema_version": 1,
        "policy_version": policy_version,
        "family_id": str(family_id),
        "child_profile_id": str(child_id),
        "issued_at": issued_at.isoformat().replace("+00:00", "Z"),
        "expires_soft_at": (issued_at + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        "key_id": "unconfigured",
        "age_band": band,
        "base_policy": base_policy,
        "app_rules": [],
        "domain_rules": [],
        "category_rules": [],
        "routines": [_bedtime(band)],
        "temporary_overrides": [],
        "communication_safety": {
            "enabled": False,
            "severity_threshold": "HIGH",
            "android_notification_signals": True,
            "android_accessibility_signals": band in {"YOUNG_CHILD", "PRETEEN"},
        },
        "signature": "",
    }
    schema = json.loads(_SCHEMA_PATH.read_text())
    errors = list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(document)
    )
    if errors:
        raise RuntimeError(
            "Generated default policy failed schema validation: "
            + "; ".join(error.message for error in errors)
        )
    return document


async def create_initial_bundle(
    session: AsyncSession,
    child_profile_id: UUID,
    parent_id: UUID,
    policy: dict[str, object],
) -> PolicyBundle:
    document = PolicyDocument(child_profile_id=child_profile_id, current_policy_version=1)
    session.add(document)
    await session.flush()
    signed = signer.sign(policy)
    bundle = PolicyBundle(
        document_id=document.id,
        child_profile_id=child_profile_id,
        policy_version=1,
        author_parent_id=parent_id,
        effective_at=datetime.now(UTC),
        previous_value=None,
        new_value=signed,
        key_id=str(signed["key_id"]),
        signature=str(signed["signature"]),
    )
    session.add(bundle)
    await session.flush()
    return bundle


async def current_bundle_for_update(
    session: AsyncSession,
    child_profile_id: UUID,
) -> PolicyBundle | None:
    """Read the current policy only after acquiring its document-wide mutex.

    A bundle lock on its own is insufficient: callers used to copy the current
    JSON before ``create_next_bundle`` acquired the document lock. Two callers
    could therefore publish monotonic versions while one silently discarded the
    other's field changes. Every policy read-modify-sign-write path uses this
    helper before it reads the document.
    """
    document = await session.scalar(
        select(PolicyDocument)
        .where(PolicyDocument.child_profile_id == child_profile_id)
        .with_for_update()
    )
    if document is None:
        return None
    bundle = await session.scalar(
        select(PolicyBundle).where(
            PolicyBundle.child_profile_id == child_profile_id,
            PolicyBundle.is_current.is_(True),
        )
    )
    return bundle if isinstance(bundle, PolicyBundle) else None


async def create_next_bundle(
    session: AsyncSession,
    child_profile_id: UUID,
    parent_id: UUID,
    new_policy: dict[str, object],
    previous_value: dict[str, object],
    effective_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> PolicyBundle:
    document = await session.scalar(
        select(PolicyDocument)
        .where(PolicyDocument.child_profile_id == child_profile_id)
        .with_for_update()
    )
    if document is None:
        raise RuntimeError("Policy document is missing")
    version = document.current_policy_version + 1
    new_policy["policy_version"] = version
    signed = signer.sign(new_policy)
    await session.execute(
        update(PolicyBundle)
        .where(
            PolicyBundle.child_profile_id == child_profile_id,
            PolicyBundle.is_current.is_(True),
        )
        .values(is_current=False, superseded_at=datetime.now(UTC))
    )
    bundle = PolicyBundle(
        document_id=document.id,
        child_profile_id=child_profile_id,
        policy_version=version,
        author_parent_id=parent_id,
        effective_at=effective_at or datetime.now(UTC),
        expires_at=expires_at,
        previous_value=previous_value,
        new_value=signed,
        key_id=str(signed["key_id"]),
        signature=str(signed["signature"]),
    )
    document.current_policy_version = version
    session.add(bundle)
    await session.flush()
    return bundle
