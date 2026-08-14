import json
from datetime import UTC, datetime

import pytest


@pytest.mark.asyncio
async def test_family_activity_and_usage_return_real_device_events(
    client, parent_a, paired_device
) -> None:
    occurred_at = datetime.now(UTC).isoformat()
    body = {
        "events": [
            {
                "event_type": "WEB_BLOCKED",
                "occurred_at": occurred_at,
                "domain": "example.org",
                "category": "EDUCATION",
            },
            {
                "event_type": "APP_USAGE",
                "occurred_at": occurred_at,
                "app_ref": "com.android.chrome",
                "category": "BROWSER",
                "duration_seconds": 300,
            },
        ]
    }
    encoded_body = json.dumps(body, separators=(",", ":")).encode()
    response = await client.post(
        "/v1/devices/me/events",
        headers=paired_device.signed_headers("/v1/devices/me/events", encoded_body),
        content=encoded_body,
    )
    assert response.status_code == 202, response.text

    headers = {"Authorization": f"Bearer {parent_a.token}"}
    families = await client.get("/v1/families", headers=headers)
    assert families.status_code == 200, families.text
    assert families.json()[0]["id"] == parent_a.family_id

    activity = await client.get(
        f"/v1/families/{parent_a.family_id}/activity", headers=headers
    )
    assert activity.status_code == 200, activity.text
    assert activity.json()[0]["event_type"] == "WEB_BLOCKED"
    assert activity.json()[0]["domain"] == "example.org"
    assert activity.json()[0]["category"] == "EDUCATION"

    usage = await client.get(
        f"/v1/families/{parent_a.family_id}/activity/usage", headers=headers
    )
    assert usage.status_code == 200, usage.text
    assert usage.json()[0] == {
        "app_ref": "com.android.chrome",
        "category": "BROWSER",
        "duration_seconds": 300,
        "event_type": "APP_USAGE",
        "occurred_at": occurred_at.replace("+00:00", "Z"),
    }
