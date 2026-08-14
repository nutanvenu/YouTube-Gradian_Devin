import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.events.models import SafetyNotification


@pytest.mark.asyncio
async def test_safety_event_routes_structured_alert_and_deduplicates(
    client, parent_a, paired_device, database_session
):
    auth = {"Authorization": f"Bearer {parent_a.token}"}
    token_response = await client.post(
        "/v1/me/push-tokens",
        json={"platform": "ANDROID", "token": "parent-device-token-" + "x" * 20},
        headers=auth,
    )
    assert token_response.status_code == 204, token_response.text
    body = {
        "events": [
            {
                "event_type": "SAFETY_RISK",
                "occurred_at": datetime(2024, 1, 2, 12, tzinfo=UTC).isoformat(),
                "category": "CONTACT",
            },
            {
                "event_type": "SAFETY_RISK",
                "occurred_at": datetime(2024, 1, 2, 12, 1, tzinfo=UTC).isoformat(),
                "category": "CONTACT",
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

    rows = list(
        (
            await database_session.scalars(select(SafetyNotification))
        ).all()
    )
    assert len(rows) == 1
    assert rows[0].severity == "HIGH"
    assert rows[0].status == "QUEUED"
