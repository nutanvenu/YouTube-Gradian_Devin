import json
from datetime import UTC, datetime, timedelta

import pytest

from app.devices.models import Device
from app.events.models import UsageAggregate


async def ingest(client, paired_device, events):
    body = {"events": events}
    encoded_body = json.dumps(body, separators=(",", ":")).encode()
    response = await client.post(
        "/v1/devices/me/events",
        headers=paired_device.signed_headers("/v1/devices/me/events", encoded_body),
        content=encoded_body,
    )
    assert response.status_code == 202, response.text


@pytest.mark.asyncio
async def test_daily_report_splits_duration_at_dst_boundary(client, parent_a, paired_device):
    await ingest(
        client,
        paired_device,
        [
            {
                "event_type": "APP_USAGE",
                "occurred_at": "2024-03-10T06:30:00Z",
                "timezone": "America/New_York",
                "app_ref": "com.example.reader",
                "category": "EDUCATION",
                "duration_seconds": 7200,
            }
        ],
    )

    response = await client.get(
        f"/v1/families/{parent_a.family_id}/usage/reports",
        params={
            "child_id": parent_a.child_id,
            "start": "2024-03-10",
            "end": "2024-03-11",
            "timezone": "America/New_York",
            "granularity": "DAILY",
        },
        headers={"Authorization": f"Bearer {parent_a.token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json() == [
        {
            "child_profile_id": parent_a.child_id,
            "period_start": "2024-03-10",
            "period_end": "2024-03-11",
            "timezone": "America/New_York",
            "duration_seconds": 7200,
            "event_count": 1,
            "by_app": {"com.example.reader": 7200},
            "by_category": {"EDUCATION": 7200},
        }
    ]


@pytest.mark.asyncio
async def test_reports_and_activity_use_latest_cumulative_snapshot_per_target(
    client, parent_a, paired_device
):
    latest = datetime.now(UTC).replace(second=0, microsecond=0)
    first = latest - timedelta(minutes=1)
    report_day = first.date().isoformat()
    next_day = (first.date() + timedelta(days=1)).isoformat()
    await ingest(
        client,
        paired_device,
        [
            {
                "event_type": "APP_USAGE",
                "occurred_at": (latest - timedelta(days=8)).isoformat().replace("+00:00", "Z"),
                "timezone": "UTC",
                "app_ref": "com.example.old",
                "duration_seconds": 9999,
            },
            {
                "event_type": "APP_USAGE",
                "occurred_at": first.isoformat().replace("+00:00", "Z"),
                "timezone": "UTC",
                "app_ref": "com.example.chrome",
                "duration_seconds": 1015,
            },
            {
                "event_type": "APP_USAGE",
                "occurred_at": latest.isoformat().replace("+00:00", "Z"),
                "timezone": "UTC",
                "app_ref": "com.example.chrome",
                "duration_seconds": 1018,
            },
        ],
    )
    headers = {"Authorization": f"Bearer {parent_a.token}"}
    report = await client.get(
        f"/v1/families/{parent_a.family_id}/usage/reports",
        params={
            "child_id": parent_a.child_id,
            "start": report_day,
            "end": next_day,
            "timezone": "UTC",
        },
        headers=headers,
    )
    activity = await client.get(
        f"/v1/families/{parent_a.family_id}/activity/usage", headers=headers
    )

    assert report.status_code == 200, report.text
    assert report.json()[0]["duration_seconds"] == 1018
    assert report.json()[0]["by_app"] == {"com.example.chrome": 1018}
    assert activity.status_code == 200, activity.text
    assert activity.json()[0]["duration_seconds"] == 1018
    assert len(activity.json()) == 1


@pytest.mark.asyncio
async def test_weekly_report_aggregates_multiple_devices_for_one_child(
    client, parent_a, paired_device, database_session
):
    await ingest(
        client,
        paired_device,
        [
            {
                "event_type": "APP_USAGE",
                "occurred_at": "2024-01-02T12:00:00Z",
                "timezone": "UTC",
                "app_ref": "com.example.reader",
                "category": "EDUCATION",
                "duration_seconds": 120,
            }
        ],
    )
    second_device = Device(
        child_profile_id=parent_a.child_id,
        platform="IOS",
        public_key="second-device-public-key",
        capabilities={},
    )
    database_session.add(second_device)
    await database_session.flush()
    database_session.add(
        UsageAggregate(
            device_id=second_device.id,
            event_type="APP_USAGE",
            occurred_at=datetime(2024, 1, 2, 13, tzinfo=UTC),
            timezone="UTC",
            app_ref="com.example.reader",
            category="EDUCATION",
            duration_seconds=180,
        )
    )
    await database_session.commit()

    response = await client.get(
        f"/v1/families/{parent_a.family_id}/usage/reports",
        params={
            "child_id": parent_a.child_id,
            "start": "2024-01-01",
            "end": "2024-01-08",
            "timezone": "UTC",
            "granularity": "WEEKLY",
        },
        headers={"Authorization": f"Bearer {parent_a.token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()[0]["duration_seconds"] == 300
    assert response.json()[0]["by_app"] == {"com.example.reader": 300}
    assert response.json()[0]["period_start"] == "2024-01-01"


@pytest.mark.asyncio
async def test_report_timezone_change_changes_local_period(client, parent_a, paired_device):
    await ingest(
        client,
        paired_device,
        [
            {
                "event_type": "APP_USAGE",
                "occurred_at": datetime(2024, 1, 2, 0, 30, tzinfo=UTC).isoformat(),
                "timezone": "UTC",
                "app_ref": "com.example.clock",
                "duration_seconds": 60,
            }
        ],
    )
    headers = {"Authorization": f"Bearer {parent_a.token}"}
    base = f"/v1/families/{parent_a.family_id}/usage/reports"
    utc_report = await client.get(
        base,
        params={
            "child_id": parent_a.child_id,
            "start": "2024-01-01",
            "end": "2024-01-03",
            "timezone": "UTC",
        },
        headers=headers,
    )
    pacific_report = await client.get(
        base,
        params={
            "child_id": parent_a.child_id,
            "start": "2024-01-01",
            "end": "2024-01-03",
            "timezone": "America/Los_Angeles",
        },
        headers=headers,
    )

    assert utc_report.status_code == 200, utc_report.text
    assert pacific_report.status_code == 200, pacific_report.text
    assert utc_report.json()[0]["period_start"] == "2024-01-02"
    assert pacific_report.json()[0]["period_start"] == "2024-01-01"


@pytest.mark.asyncio
async def test_report_rejects_invalid_timezone(client, parent_a):
    response = await client.get(
        f"/v1/families/{parent_a.family_id}/usage/reports",
        params={
            "start": "2024-01-01",
            "end": "2024-01-02",
            "timezone": "Not/AnIanaZone",
        },
        headers={"Authorization": f"Bearer {parent_a.token}"},
    )
    assert response.status_code == 422
