import json

import pytest


@pytest.mark.asyncio
async def test_device_inventory_sync_and_parent_review_persist(
    client, parent_a, paired_device
) -> None:
    body = {
        "apps": [
            {
                "platform_app_id": "com.example.child",
                "display_name": "Example Child",
                "category": "GAMES",
                "observed_at": "2026-08-14T20:00:00Z",
            }
        ]
    }
    encoded_body = json.dumps(body, separators=(",", ":")).encode()
    upload = await client.post(
        "/v1/devices/me/inventory",
        headers=paired_device.signed_headers("/v1/devices/me/inventory", encoded_body),
        content=encoded_body,
    )
    assert upload.status_code == 202, upload.text

    parent_headers = {"Authorization": f"Bearer {parent_a.token}"}
    inventory = await client.get(
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}/inventory",
        headers=parent_headers,
    )
    assert inventory.status_code == 200, inventory.text
    assert inventory.json() == [
        {
            "platform_app_id": "com.example.child",
            "display_name": "Example Child",
            "category": "GAMES",
            "observed_at": "2026-08-14T20:00:00Z",
            "reviewed": False,
        }
    ]

    review = await client.post(
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}/inventory/com.example.child/review",
        headers=parent_headers,
    )
    assert review.status_code == 204, review.text

    reviewed = await client.get(
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}/inventory",
        headers=parent_headers,
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()[0]["reviewed"] is True

    repeat_upload = await client.post(
        "/v1/devices/me/inventory",
        headers=paired_device.signed_headers("/v1/devices/me/inventory", encoded_body),
        content=encoded_body,
    )
    assert repeat_upload.status_code == 202, repeat_upload.text
    preserved = await client.get(
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}/inventory",
        headers=parent_headers,
    )
    assert preserved.json()[0]["reviewed"] is True


@pytest.mark.asyncio
async def test_inventory_requires_child_device_and_family_guardianship(
    client, parent_a, parent_b, paired_device, revoked_device
) -> None:
    body = {"apps": []}
    encoded_body = json.dumps(body, separators=(",", ":")).encode()
    revoked_upload = await client.post(
        "/v1/devices/me/inventory",
        headers=revoked_device.signed_headers("/v1/devices/me/inventory", encoded_body),
        content=encoded_body,
    )
    assert revoked_upload.status_code == 401, revoked_upload.text

    response = await client.get(
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}/inventory",
        headers={"Authorization": f"Bearer {parent_b.token}"},
    )
    assert response.status_code == 404, response.text
