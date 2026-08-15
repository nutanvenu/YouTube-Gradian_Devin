from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..children.models import ChildProfile
from ..devices.models import Device
from .models import UsageAggregate


def _period_start(local_date: date, granularity: Literal["DAILY", "WEEKLY"]) -> date:
    if granularity == "DAILY":
        return local_date
    return local_date - timedelta(days=local_date.weekday())


def _next_period_start(
    period_start: date, granularity: Literal["DAILY", "WEEKLY"]
) -> date:
    return period_start + timedelta(days=1 if granularity == "DAILY" else 7)


def _utc_midnight(day: date, timezone: ZoneInfo) -> datetime:
    return datetime.combine(day, datetime.min.time(), tzinfo=timezone).astimezone(UTC)


def _target_key(row: UsageAggregate) -> str:
    if row.app_ref:
        return f"APP:{row.app_ref}"
    if row.category:
        return f"CATEGORY:{row.category}"
    return "DEVICE"


def latest_usage_snapshots(
    rows: Iterable[tuple[UsageAggregate, UUID]],
    *,
    timezone: ZoneInfo | None = None,
) -> list[tuple[UsageAggregate, UUID]]:
    latest: dict[tuple[UUID, UUID, date, str], tuple[UsageAggregate, UUID]] = {}
    for row, child_id in rows:
        row_timezone = timezone
        if row_timezone is None:
            try:
                row_timezone = ZoneInfo(row.timezone)
            except Exception:
                row_timezone = ZoneInfo("UTC")
        key = (
            child_id,
            row.device_id,
            row.occurred_at.astimezone(row_timezone).date(),
            _target_key(row),
        )
        current = latest.get(key)
        if current is None or row.occurred_at > current[0].occurred_at:
            latest[key] = (row, child_id)
    return sorted(latest.values(), key=lambda item: item[0].occurred_at)


async def usage_report(
    session: AsyncSession,
    *,
    family_id: UUID,
    child_id: UUID | None,
    start: date,
    end: date,
    timezone: str,
    granularity: Literal["DAILY", "WEEKLY"],
) -> list[dict[str, object]]:
    report_timezone = ZoneInfo(timezone)
    start_utc = _utc_midnight(start, report_timezone)
    end_utc = _utc_midnight(end, report_timezone)
    query = (
        select(UsageAggregate, Device.child_profile_id)
        .join(Device, Device.id == UsageAggregate.device_id)
        .join(ChildProfile, ChildProfile.id == Device.child_profile_id)
        .where(
            ChildProfile.family_id == family_id,
            UsageAggregate.occurred_at >= start_utc,
            UsageAggregate.occurred_at < end_utc,
        )
        .order_by(UsageAggregate.occurred_at)
    )
    if child_id is not None:
        query = query.where(ChildProfile.id == child_id)
    rows = latest_usage_snapshots(
        (await session.execute(query)).tuples().all(),
        timezone=report_timezone,
    )
    buckets: dict[tuple[UUID, date], dict[str, Any]] = {}
    for row, row_child_id in rows:
        if row.duration_seconds <= 0:
            continue
        local_date = row.occurred_at.astimezone(report_timezone).date()
        period_start = _period_start(local_date, granularity)
        period_end = _next_period_start(period_start, granularity)
        key = (row_child_id, period_start)
        bucket = buckets.setdefault(
            key,
            {
                "child_profile_id": row_child_id,
                "period_start": period_start,
                "period_end": period_end,
                "timezone": timezone,
                "duration_seconds": 0,
                "event_count": 0,
                "by_app": defaultdict(int),
                "by_category": defaultdict(int),
            },
        )
        bucket["duration_seconds"] += row.duration_seconds
        bucket["event_count"] += 1
        bucket["by_app"][row.app_ref or "Unknown"] += row.duration_seconds
        bucket["by_category"][row.category or "Unknown"] += row.duration_seconds
    return [
        {
            **bucket,
            "by_app": dict(bucket["by_app"]),
            "by_category": dict(bucket["by_category"]),
        }
        for bucket in sorted(
            buckets.values(),
            key=lambda value: (value["period_start"], str(value["child_profile_id"])),
        )
    ]
