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
            "date_of_birth": "2018-08-15",
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


@pytest.mark.asyncio
async def test_child_age_or_timezone_update_publishes_a_signed_policy_without_erasing_rules(
    client, parent_a
) -> None:
    headers = {"Authorization": f"Bearer {parent_a.token}"}
    initial = await client.post(
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}/policy/mutations",
        headers=headers,
        json={"operation": "APP_BLOCK", "target": "com.example.browser"},
    )
    assert initial.status_code == 200

    updated = await client.patch(
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}",
        headers=headers,
        json={"date_of_birth": "2011-08-15", "timezone": "America/Los_Angeles"},
    )

    assert updated.status_code == 200
    policy = updated.json()["policy_document"]
    assert updated.json()["age_band"] == "TEEN"
    assert policy["policy_version"] == 3
    assert policy["age_band"] == "TEEN"
    assert policy["base_policy"]["timezone"] == "America/Los_Angeles"
    assert policy["signature"]
    assert len(policy["app_rules"]) == 1
    assert policy["app_rules"][0]["app_ref"] == "com.example.browser"
    assert policy["app_rules"][0]["action"] == "BLOCK"
