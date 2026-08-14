import pytest
from conftest import PairedDevice, ParentFamily


@pytest.mark.asyncio
async def test_refresh_rotation_and_reuse_revokes_family(client, parent_a: ParentFamily) -> None:
    login = await client.post(
        "/v1/auth/login",
        json={"email": "invalid@example.com", "password": "wrong password"},
    )
    assert login.status_code == 401

    signup = await client.post(
        "/v1/auth/signup",
        json={"email": "rotate@example.com", "password": "correct horse battery staple"},
    )
    refresh = signup.json()["refresh_token"]
    rotated = await client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert rotated.status_code == 200
    reused = await client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert reused.status_code == 401
    assert (
        await client.post(
            "/v1/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]}
        )
    ).status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client) -> None:
    signup = await client.post(
        "/v1/auth/signup",
        json={"email": "logout@example.com", "password": "correct horse battery staple"},
    )
    refresh = signup.json()["refresh_token"]
    assert await client.post("/v1/auth/logout", json={"refresh_token": refresh})
    revoked = await client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert revoked.status_code == 401


@pytest.mark.asyncio
async def test_validation_errors_have_stable_shape(client) -> None:
    response = await client.post("/v1/auth/signup", json={"email": "not-an-email", "password": "x"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_login_rate_limit_trips(client) -> None:
    for _ in range(10):
        response = await client.post(
            "/v1/auth/login",
            json={"email": "rate@example.com", "password": "wrong password"},
        )
        assert response.status_code == 401
    response = await client.post(
        "/v1/auth/login",
        json={"email": "rate@example.com", "password": "wrong password"},
    )
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_device_routes_and_minimized_event_validation(
    client, paired_device: PairedDevice
) -> None:
    device_headers = {"Authorization": f"Bearer {paired_device.device_token}"}
    policy = await client.get("/v1/devices/me/policy", headers=device_headers)
    assert policy.status_code == 200
    assert (
        await client.post(
            "/v1/devices/me/policy/ack",
            json={"policy_version": 1},
            headers=device_headers,
        )
    ).status_code == 204
    assert (
        await client.post(
            "/v1/devices/me/heartbeat",
            json={"protection_state": "PROTECTED"},
            headers=device_headers,
        )
    ).status_code == 204
    rejected = await client.post(
        "/v1/devices/me/events",
        json={
            "events": [
                {
                    "event_type": "URL",
                    "occurred_at": "2026-01-01T00:00:00Z",
                    "raw_content": "secret",
                }
            ]
        },
        headers=device_headers,
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_credentials_cannot_cross_parent_and_device_routes(
    client, paired_device: PairedDevice
) -> None:
    parent_headers = {"Authorization": f"Bearer {paired_device.parent.token}"}
    device_headers = {"Authorization": f"Bearer {paired_device.device_token}"}
    assert (await client.get("/v1/devices/me/policy", headers=parent_headers)).status_code == 401
    assert (
        await client.get(f"/v1/families/{paired_device.parent.family_id}", headers=device_headers)
    ).status_code == 401
