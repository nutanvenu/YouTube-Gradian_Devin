from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Literal
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
            UsageAggregate.duration_seconds > 0,
        )
        .order_by(UsageAggregate.occurred_at)
    )
    if child_id is not None:
        query = query.where(ChildProfile.id == child_id)
    rows = list((await session.execute(query)).all())
    buckets: dict[tuple[UUID, date], dict[str, object]] = {}
    for row, row_child_id in rows:
        remaining_start = row.occurred_at
        remaining_end = row.occurred_at + timedelta(seconds=row.duration_seconds)
        while remaining_start < remaining_end:
            local_start = remaining_start.astimezone(report_timezone)
            period_start = _period_start(local_start.date(), granularity)
            period_end = _next_period_start(period_start, granularity)
            boundary = _utc_midnight(period_end, report_timezone)
            segment_end = min(remaining_end, boundary)
            seconds = max(0, int((segment_end - remaining_start).total_seconds()))
            if seconds:
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
                bucket["duration_seconds"] += seconds
                bucket["event_count"] += 1
                bucket["by_app"][row.app_ref or "Unknown"] += seconds
                bucket["by_category"][row.category or "Unknown"] += seconds
            remaining_start = segment_end
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
