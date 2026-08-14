import pytest

from app.api.routes import signer
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
