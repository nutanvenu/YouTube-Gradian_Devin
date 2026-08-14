from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_signup_family_child_and_tenant_isolation(client) -> None:
    email = f"{uuid4()}@example.com"
    signup = await client.post(
        "/v1/auth/signup",
        json={"email": email, "password": "correct horse battery staple"},
    )
    assert signup.status_code == 201
    token = signup.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    family = await client.post("/v1/families", json={"name": "Home"}, headers=headers)
    assert family.status_code == 201
    family_id = family.json()["id"]
    child = await client.post(
        f"/v1/families/{family_id}/children",
        json={
            "name": "Alex",
            "date_of_birth": "2017-08-15",
            "timezone": "America/New_York",
        },
        headers=headers,
    )
    assert child.status_code == 201
    assert child.json()["age_band"] == "YOUNG_CHILD"

    other = await client.post(
        "/v1/auth/signup",
        json={"email": f"{uuid4()}@example.com", "password": "correct horse battery staple"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    denied = await client.get(f"/v1/families/{family_id}", headers=other_headers)
    assert denied.status_code == 404
