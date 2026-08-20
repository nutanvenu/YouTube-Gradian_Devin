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

UNATTRIBUTED_CATEGORY = "UNATTRIBUTED"
UNATTRIBUTED_EVENT_TYPE = "UNATTRIBUTED_USAGE"


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
    if row.snapshot_key:
        return row.snapshot_key
    if row.app_ref:
        return f"APP:{row.app_ref}"
    if row.category:
        return f"CATEGORY:{row.category}"
    return "DEVICE"


def _local_day(row: UsageAggregate, timezone: ZoneInfo | None) -> date:
    row_timezone = timezone
    if row_timezone is None:
        try:
            row_timezone = ZoneInfo(row.timezone)
        except Exception:
            row_timezone = ZoneInfo("UTC")
    return row.occurred_at.astimezone(row_timezone).date()


def _unattributed_snapshot(
    reference: UsageAggregate,
    duration_seconds: int,
) -> UsageAggregate:
    """Represent roll-up time that Android cannot safely attribute in detail."""
    return UsageAggregate(
        device_id=reference.device_id,
        event_type=UNATTRIBUTED_EVENT_TYPE,
        occurred_at=reference.occurred_at,
        timezone=reference.timezone,
        app_ref=None,
        category=UNATTRIBUTED_CATEGORY,
        duration_seconds=duration_seconds,
        snapshot_day=reference.snapshot_day,
        snapshot_key=f"CATEGORY:{UNATTRIBUTED_CATEGORY}",
    )


def latest_usage_snapshots(
    rows: Iterable[tuple[UsageAggregate, UUID]],
    *,
    timezone: ZoneInfo | None = None,
) -> list[tuple[UsageAggregate, UUID]]:
    latest: dict[tuple[UUID, UUID, date, str], tuple[UsageAggregate, UUID]] = {}
    for row, child_id in rows:
        key = (
            child_id,
            row.device_id,
            _local_day(row, timezone),
            _target_key(row),
        )
        current = latest.get(key)
        if current is None or row.occurred_at > current[0].occurred_at:
            latest[key] = (row, child_id)
    return sorted(latest.values(), key=lambda item: item[0].occurred_at)


def resolved_usage_snapshots(
    rows: Iterable[tuple[UsageAggregate, UUID]],
    *,
    timezone: ZoneInfo | None = None,
) -> list[tuple[UsageAggregate, UUID]]:
    """Choose one roll-up level per device/day without double-counting or loss.

    Device collectors may send app, category, and device cumulative summaries for
    the same day. The parent total is the maximum independently reported roll-up
    (device, category sum, or app sum), never their sum. App rows are retained
    when available, otherwise category rows. If that detailed view is smaller
    than the best roll-up, a synthetic UNATTRIBUTED row honestly exposes the
    residual instead of either double-counting or silently under-reporting it.
    """
    latest = latest_usage_snapshots(rows, timezone=timezone)
    by_device_day: dict[
        tuple[UUID, UUID, date], list[tuple[UsageAggregate, UUID]]
    ] = defaultdict(list)
    for row, child_id in latest:
        key = (child_id, row.device_id, _local_day(row, timezone))
        by_device_day[key].append((row, child_id))

    selected: list[tuple[UsageAggregate, UUID]] = []
    for candidates in by_device_day.values():
        app_rows = [item for item in candidates if item[0].app_ref]
        category_rows = [item for item in candidates if item[0].category and not item[0].app_ref]
        device_rows = [item for item in candidates if not item[0].app_ref and not item[0].category]
        detailed_rows = app_rows or category_rows
        app_total = sum(item[0].duration_seconds for item in app_rows)
        category_total = sum(item[0].duration_seconds for item in category_rows)
        device_total = sum(item[0].duration_seconds for item in device_rows)
        total = max(app_total, category_total, device_total)
        selected.extend(detailed_rows)
        detailed_total = sum(item[0].duration_seconds for item in detailed_rows)
        if total > detailed_total:
            reference, child_id = max(candidates, key=lambda item: item[0].occurred_at)
            selected.append((_unattributed_snapshot(reference, total - detailed_total), child_id))
    return sorted(selected, key=lambda item: item[0].occurred_at)


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
    rows = resolved_usage_snapshots(
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
                "unattributed_seconds": 0,
                "coverage": "COMPLETE",
            },
        )
        bucket["duration_seconds"] += row.duration_seconds
        bucket["event_count"] += 1
        bucket["by_app"][row.app_ref or "Unknown"] += row.duration_seconds
        bucket["by_category"][row.category or "Unknown"] += row.duration_seconds
        if row.event_type == UNATTRIBUTED_EVENT_TYPE:
            bucket["unattributed_seconds"] += row.duration_seconds
            bucket["coverage"] = "PARTIAL"
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
