import pytest

from app.api.route_handlers import signer
from app.core.config import get_settings


@pytest.mark.asyncio
async def test_signed_policy_and_requests_round_trip(client, paired_device) -> None:
    device_headers = {"Authorization": f"Bearer {paired_device.device_token}"}
    policy = await client.get("/v1/devices/me/policy", headers=device_headers)
    assert policy.status_code == 200
    body = policy.json()
    assert body["bundle"]["signature"]
    assert body["bundle"]["key_id"] == get_settings().policy_key_id
    request = await client.post(
        "/v1/devices/me/requests",
        headers={**device_headers, "Idempotency-Key": "request-1"},
        json={"request_type": "UNBLOCK_APP", "subject": "com.example.app"},
    )
    assert request.status_code == 201
    replay = await client.post(
        "/v1/devices/me/requests",
        headers={**device_headers, "Idempotency-Key": "request-1"},
        json={"request_type": "UNBLOCK_APP", "subject": "com.example.app"},
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == request.json()["id"]
    public_key = await client.get("/v1/policy/public-key")
    assert public_key.status_code == 200
    assert public_key.json()["key_id"] == get_settings().policy_key_id
    assert signer.public_key() == public_key.json()["public_key"]


@pytest.mark.asyncio
async def test_parent_policy_mutation_is_versioned_and_idempotent(client, parent_a) -> None:
    headers = {
        "Authorization": f"Bearer {parent_a.token}",
        "Idempotency-Key": "policy-1",
    }
    response = await client.post(
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}/policy/mutations",
        headers=headers,
        json={"operation": "APP_DAILY_MINUTES", "target": "com.example.app", "value": 30},
    )
    assert response.status_code == 200
    assert response.json()["policy_version"] == 2
    replay = await client.post(
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}/policy/mutations",
        headers=headers,
        json={"operation": "APP_DAILY_MINUTES", "target": "com.example.app", "value": 30},
    )
    assert replay.status_code == 200
    assert replay.json()["bundle"]["signature"] == response.json()["bundle"]["signature"]


@pytest.mark.asyncio
async def test_parent_policy_override_surface_records_audit_fields(client, parent_a) -> None:
    headers = {"Authorization": f"Bearer {parent_a.token}"}
    operations = [
        {
            "operation": "APP_SCHEDULE",
            "target": "com.example.app",
            "value": {"days": [1, 2, 3, 4, 5], "start": "08:00", "end": "18:00"},
        },
        {
            "operation": "WEB_CATEGORY_BLOCK",
            "target": "SOCIAL_MEDIA",
        },
        {
            "operation": "UNKNOWN_APP_POLICY",
            "target": "base_policy",
            "value": "LIMIT_AND_NOTIFY",
        },
        {
            "operation": "ROUTINE_CREATE",
            "target": "school",
            "value": {
                "routine_id": "school",
                "name": "School",
                "kind": "SCHEDULED",
                "window": {"days": [1, 2, 3, 4, 5], "start": "08:00", "end": "15:00"},
            },
        },
    ]
    previous_version = 1
    for operation in operations:
        response = await client.post(
            f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}/policy/mutations",
            headers=headers,
            json=operation,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["policy_version"] == previous_version + 1
        assert body["author_parent_id"]
        assert body["mutation_at"]
        assert body["effective_at"]
        assert body["previous_value"]["operation"] == operation["operation"]
        assert body["new_value"]["policy_version"] == body["policy_version"]
        assert body["superseded_policy_version"] == previous_version
        previous_version += 1


@pytest.mark.asyncio
async def test_manual_routine_activation_is_carried_in_signed_policy(client, parent_a) -> None:
    headers = {"Authorization": f"Bearer {parent_a.token}"}
    created = await client.post(
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}/policy/mutations",
        headers=headers,
        json={
            "operation": "ROUTINE_CREATE",
            "target": "focus",
            "value": {
                "routine_id": "focus",
                "name": "Focus",
                "kind": "MANUAL",
                "blocked_apps": ["com.example.video"],
            },
        },
    )
    assert created.status_code == 200
    activated = await client.post(
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}/policy/mutations",
        headers=headers,
        json={"operation": "ROUTINE_ACTIVATE", "target": "focus"},
    )
    assert activated.status_code == 200
    assert activated.json()["bundle"]["base_policy"]["current_manual_routine_id"] == "focus"
    deactivated = await client.post(
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}/policy/mutations",
        headers=headers,
        json={"operation": "ROUTINE_DEACTIVATE", "target": "focus"},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["bundle"]["base_policy"]["current_manual_routine_id"] is None


@pytest.mark.asyncio
async def test_device_push_token_registration_is_device_scoped(client, paired_device) -> None:
    headers = {"Authorization": f"Bearer {paired_device.device_token}"}
    response = await client.post(
        "/v1/devices/me/push-tokens",
        headers=headers,
        json={"platform": "ANDROID", "token": "device-token-" + "x" * 20},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_request_approval_retry_replays_without_new_policy_version(
    client, paired_device
) -> None:
    device_headers = {"Authorization": f"Bearer {paired_device.device_token}"}
    parent_headers = {"Authorization": f"Bearer {paired_device.parent.token}"}
    created = await client.post(
        "/v1/devices/me/requests",
        headers=device_headers,
        json={"request_type": "UNBLOCK_APP", "subject": "com.example.app"},
    )
    assert created.status_code == 201
    path = (
        f"/v1/families/{paired_device.parent.family_id}/requests/"
        f"{created.json()['id']}/approve"
    )
    headers = {**parent_headers, "Idempotency-Key": "approval-retry"}
    first = await client.post(path, headers=headers, json={"reason": "Approved"})
    second = await client.post(path, headers=headers, json={"reason": "Approved"})
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["state"] == second.json()["state"] == "APPROVED"
