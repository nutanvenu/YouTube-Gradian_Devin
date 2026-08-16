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
            "version_name": None,
            "first_seen_at": None,
            "last_seen_at": "2026-08-14T20:00:00Z",
            "installation_state": None,
            "capability_sources": [],
            "inventory_completeness": None,
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


@pytest.mark.asyncio
async def test_inventory_upload_deduplicates_apps_and_preserves_review(
    client, parent_a, paired_device
) -> None:
    body = {
        "apps": [
            {
                "platform_app_id": "com.example.duplicate",
                "display_name": "First name",
                "category": "GAMES",
                "observed_at": "2026-08-14T20:00:00Z",
            },
            {
                "platform_app_id": "com.example.duplicate",
                "display_name": "Latest name",
                "category": "EDUCATION",
                "observed_at": "2026-08-14T20:01:00Z",
            },
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
    path = (
        f"/v1/families/{parent_a.family_id}/children/"
        f"{parent_a.child_id}/inventory"
    )
    inventory = await client.get(path, headers=parent_headers)
    assert inventory.status_code == 200, inventory.text
    assert inventory.json() == [
        {
            "platform_app_id": "com.example.duplicate",
            "display_name": "Latest name",
            "category": "EDUCATION",
            "observed_at": "2026-08-14T20:01:00Z",
            "reviewed": False,
            "version_name": None,
            "first_seen_at": None,
            "last_seen_at": "2026-08-14T20:01:00Z",
            "installation_state": None,
            "capability_sources": [],
            "inventory_completeness": None,
        }
    ]

    review = await client.post(f"{path}/com.example.duplicate/review", headers=parent_headers)
    assert review.status_code == 204, review.text

    repeat = {
        "apps": [
            {
                "platform_app_id": "com.example.duplicate",
                "display_name": "Changed name",
                "category": "EDUCATION",
                "observed_at": "2026-08-14T20:02:00Z",
            }
        ]
    }
    encoded_repeat = json.dumps(repeat, separators=(",", ":")).encode()
    repeat_upload = await client.post(
        "/v1/devices/me/inventory",
        headers=paired_device.signed_headers("/v1/devices/me/inventory", encoded_repeat),
        content=encoded_repeat,
    )
    assert repeat_upload.status_code == 202, repeat_upload.text

    preserved = await client.get(path, headers=parent_headers)
    assert preserved.json() == [
        {
            "platform_app_id": "com.example.duplicate",
            "display_name": "Changed name",
            "category": "EDUCATION",
            "observed_at": "2026-08-14T20:02:00Z",
            "reviewed": True,
            "version_name": None,
            "first_seen_at": None,
            "last_seen_at": "2026-08-14T20:02:00Z",
            "installation_state": None,
            "capability_sources": [],
            "inventory_completeness": None,
        }
    ]


@pytest.mark.asyncio
async def test_inventory_propagates_lifecycle_metadata_and_preserves_it_for_legacy_uploads(
    client, parent_a, paired_device
) -> None:
    body = {
        "apps": [
            {
                "platform_app_id": "com.example.lifecycle",
                "display_name": "Lifecycle app",
                "category": "GAMES",
                "observed_at": "2026-08-14T20:00:00Z",
                "version_name": "1.2.3",
                "first_seen_at": "2026-08-01T10:00:00Z",
                "last_seen_at": "2026-08-14T20:00:00Z",
                "installation_state": "INSTALLED",
                "capability_sources": ["LAUNCHER", "ACCESSIBILITY_FOREGROUND"],
                "inventory_completeness": "PARTIAL",
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

    # A prior mobile build can still send the old payload without erasing the
    # lifecycle state reported by a newer child app.
    legacy = {
        "apps": [{
            "platform_app_id": "com.example.lifecycle",
            "display_name": "Lifecycle app renamed",
            "category": "EDUCATION",
            "observed_at": "2026-08-14T20:01:00Z",
        }]
    }
    encoded_legacy = json.dumps(legacy, separators=(",", ":")).encode()
    repeat = await client.post(
        "/v1/devices/me/inventory",
        headers=paired_device.signed_headers("/v1/devices/me/inventory", encoded_legacy),
        content=encoded_legacy,
    )
    assert repeat.status_code == 202, repeat.text

    inventory = await client.get(
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}/inventory",
        headers={"Authorization": f"Bearer {parent_a.token}"},
    )
    assert inventory.status_code == 200, inventory.text
    assert inventory.json() == [{
        "platform_app_id": "com.example.lifecycle",
        "display_name": "Lifecycle app renamed",
        "category": "EDUCATION",
        "observed_at": "2026-08-14T20:01:00Z",
        "reviewed": False,
        "version_name": "1.2.3",
        "first_seen_at": "2026-08-01T10:00:00Z",
        "last_seen_at": "2026-08-14T20:01:00Z",
        "installation_state": "INSTALLED",
        "capability_sources": ["LAUNCHER", "ACCESSIBILITY_FOREGROUND"],
        "inventory_completeness": "PARTIAL",
    }]
