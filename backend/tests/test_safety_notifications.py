import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.children.models import ChildProfile
from app.events.models import SafetyEvent, SafetyNotification


@pytest.mark.asyncio
async def test_safety_event_routes_structured_alert_and_deduplicates(
    client, parent_a, paired_device, database_session
):
    auth = {"Authorization": f"Bearer {parent_a.token}"}
    child = await database_session.get(ChildProfile, paired_device.parent.child_id)
    assert child is not None
    child.policy_document = {
        **child.policy_document,
        "communication_safety": {
            **child.policy_document["communication_safety"],
            "enabled": True,
        },
    }
    await database_session.commit()
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
                "severity": "HIGH",
                "confidence": 0.91,
                "reason_code": "RULE_CONTACT_CONTEXT",
            },
            {
                "event_type": "SAFETY_RISK",
                "occurred_at": datetime(2024, 1, 2, 12, 1, tzinfo=UTC).isoformat(),
                "category": "CONTACT",
                "severity": "HIGH",
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
    assert len(rows) == 2
    assert {row.severity for row in rows} == {"HIGH"}
    assert {row.status for row in rows} == {"QUEUED", "SUPPRESSED_DEDUPE"}
    safety_events = list((await database_session.scalars(select(SafetyEvent))).all())
    assert {event.confidence for event in safety_events} == {0.91, None}
    assert {event.reason_code for event in safety_events} == {"RULE_CONTACT_CONTEXT", None}


@pytest.mark.asyncio
async def test_safety_routing_persists_quiet_dedupe_and_rate_outcomes(
    client, parent_a, paired_device, database_session
):
    auth = {"Authorization": f"Bearer {parent_a.token}"}
    child = await database_session.get(ChildProfile, paired_device.parent.child_id)
    assert child is not None
    child.policy_document = {
        **child.policy_document,
        "communication_safety": {
            **child.policy_document["communication_safety"],
            "enabled": True,
        },
    }
    await database_session.commit()
    token_response = await client.post(
        "/v1/me/push-tokens",
        json={"platform": "ANDROID", "token": "parent-routing-token-" + "x" * 20},
        headers=auth,
    )
    assert token_response.status_code == 204, token_response.text
    events = [
        {
            "event_type": "SAFETY_RISK",
            "occurred_at": datetime(2024, 1, 2, 12, tzinfo=UTC).isoformat(),
            "category": "CONTACT",
            "severity": "HIGH",
        },
        {
            "event_type": "SAFETY_RISK",
            "occurred_at": datetime(2024, 1, 2, 12, 1, tzinfo=UTC).isoformat(),
            "category": "CONTACT",
            "severity": "HIGH",
        },
        {
            "event_type": "SAFETY_RISK",
            "occurred_at": datetime(2024, 1, 2, 22, tzinfo=UTC).isoformat(),
            "category": "QUIET",
            "severity": "MEDIUM",
        },
    ]
    events.extend(
        {
            "event_type": "SAFETY_RISK",
            "occurred_at": datetime(2024, 1, 2, 13, index, tzinfo=UTC).isoformat(),
            "category": f"RATE_{index}",
            "severity": "HIGH",
        }
        for index in range(5)
    )
    body = json.dumps({"events": events}, separators=(",", ":")).encode()
    response = await client.post(
        "/v1/devices/me/events",
        headers=paired_device.signed_headers("/v1/devices/me/events", body),
        content=body,
    )
    assert response.status_code == 202, response.text
    rows = list((await database_session.scalars(select(SafetyNotification))).all())
    statuses = [row.status for row in rows]
    assert "QUEUED" in statuses
    assert "SUPPRESSED_DEDUPE" in statuses
    assert "SUPPRESSED_QUIET" in statuses
    assert "SUPPRESSED_RATE" in statuses
