import hashlib
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..children.models import ChildProfile
from ..devices.models import Device
from ..families.models import FamilyGuardian
from ..push.models import PushToken
from ..push.service import PushSender
from .models import SafetyEvent, SafetyNotification

_QUIET_START = 21
_QUIET_END = 7
_RATE_LIMIT = 5
_IMMEDIATE_SEVERITIES = {"HIGH", "CRITICAL"}
_SUMMARY_SEVERITY = "MEDIUM"
_SEVERITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def safety_severity(event: SafetyEvent) -> str:
    if event.severity:
        return (
            event.severity
            if event.severity in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
            else "MEDIUM"
        )
    event_type = event.event_type.upper()
    if "CRITICAL" in event_type or "IMMINENT" in event_type:
        return "CRITICAL"
    if "RISK" in event_type or "SELF_HARM" in event_type or "EXPLOIT" in event_type:
        return "HIGH"
    return "MEDIUM" if event_type.startswith("SAFETY") else "LOW"


def age_band_allows(age_band: str, severity: str) -> bool:
    if age_band in {"YOUNG_CHILD", "PRETEEN"}:
        return True
    if age_band == "TEEN":
        return severity in {"HIGH", "CRITICAL"}
    return severity == "CRITICAL"


def in_quiet_hours(occurred_at: datetime, timezone: str) -> bool:
    local_hour = occurred_at.astimezone(ZoneInfo(timezone)).hour
    return local_hour >= _QUIET_START or local_hour < _QUIET_END


def _dedupe_key(event: SafetyEvent, severity: str) -> str:
    raw = "|".join(
        [
            event.event_type,
            event.app_ref or "",
            event.domain or "",
            event.category or "",
            severity,
            str(int(event.occurred_at.timestamp()) // 600),
        ]
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def notification_body(event: SafetyEvent, severity: str) -> str:
    if event.category == "SELF_HARM" and severity in {"HIGH", "CRITICAL"}:
        return (
            "Guardian detected a high-risk self-harm signal in a notification on your "
            "child's Android device. The message text was analyzed on the device and "
            "wasn't stored. Consider checking in with your child."
        )
    return (
        f"Guardian detected a {severity.lower()} {event.category or 'safety'} signal "
        f"from {event.app_ref or 'a communication app'}."
    )


async def route_safety_notifications(
    session: AsyncSession,
    events: Iterable[SafetyEvent],
    sender: PushSender,
    *,
    now: datetime | None = None,
) -> list[tuple[UUID, dict[str, object]]]:
    now = now or datetime.now(UTC)
    deliveries: list[tuple[UUID, dict[str, object]]] = []
    for event in events:
        severity = safety_severity(event)
        child = await session.scalar(
            select(ChildProfile)
            .join(Device, Device.child_profile_id == ChildProfile.id)
            .where(Device.id == event.device_id)
        )
        if child is None or not age_band_allows(child.age_band, severity):
            continue
        communication = child.policy_document.get("communication_safety", {})
        if not isinstance(communication, dict) or communication.get("enabled") is not True:
            continue
        threshold = communication.get("severity_threshold", "HIGH")
        if threshold not in _SEVERITY_RANK:
            threshold = "HIGH"
        parent_ids = set(
            (
                await session.scalars(
                    select(FamilyGuardian.parent_id).where(
                        FamilyGuardian.family_id == child.family_id
                    )
                )
            ).all()
        )
        for parent_id in parent_ids:
            dedupe_key = _dedupe_key(event, severity)
            existing = await session.scalar(
                select(SafetyNotification)
                .where(
                    SafetyNotification.parent_id == parent_id,
                    SafetyNotification.dedupe_key == dedupe_key,
                )
                .order_by(SafetyNotification.created_at.desc())
            )
            recent = await session.scalar(
                select(func.count(SafetyNotification.id)).where(
                    SafetyNotification.parent_id == parent_id,
                    SafetyNotification.created_at >= now - timedelta(hours=1),
                )
            ) or 0
            quiet = in_quiet_hours(event.occurred_at, child.timezone)
            if existing is not None:
                status = "SUPPRESSED_DEDUPE"
            elif recent >= _RATE_LIMIT:
                status = "SUPPRESSED_RATE"
            elif quiet and severity != "CRITICAL":
                status = "SUPPRESSED_QUIET"
            elif severity == "LOW":
                status = "SUPPRESSED_TREND"
            elif severity == _SUMMARY_SEVERITY:
                status = (
                    "QUEUED_SUMMARY"
                    if _SEVERITY_RANK[threshold] <= _SEVERITY_RANK[severity]
                    else "SUPPRESSED_SUMMARY"
                )
            elif _SEVERITY_RANK[severity] < _SEVERITY_RANK[threshold]:
                status = "SUPPRESSED_THRESHOLD"
            else:
                status = "QUEUED"
            session.add(
                SafetyNotification(
                    parent_id=parent_id,
                    child_profile_id=child.id,
                    safety_event_id=event.id,
                    dedupe_key=dedupe_key,
                    severity=severity,
                    status=status,
                )
            )
            if status == "QUEUED_SUMMARY":
                continue
            if status == "QUEUED":
                token_exists = await session.scalar(
                    select(PushToken.id).where(
                        PushToken.parent_id == parent_id, PushToken.active.is_(True)
                    )
                )
                if token_exists is not None:
                    deliveries.append(
                        (
                            parent_id,
                            {
                                "type": "SAFETY_ALERT",
                                "severity": severity,
                                "event_type": event.event_type,
                                "category": event.category,
                                "body": notification_body(event, severity),
                                "child_profile_id": str(child.id),
                            },
                        )
                    )
    return deliveries
