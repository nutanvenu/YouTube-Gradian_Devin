import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from app.reputation.signing import verify_signed_reputation


@pytest.mark.asyncio
async def test_empty_reputation_sync_has_no_shipping_fixture_and_classification_stays_minimized(
    client, parent_a, paired_device
) -> None:
    response = await client.get(
        "/v1/devices/me/reputation?version=0",
        headers={"Authorization": f"Bearer {paired_device.device_token}"},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"current_version": 0, "bundle": None, "deltas": []}

    encoded = json.dumps({"identifier": "unknown.example"}, separators=(",", ":")).encode()
    classified = await client.post(
        "/v1/devices/me/reputation/classify",
        headers={
            "Authorization": f"Bearer {paired_device.device_token}",
            **paired_device.signed_headers(
                "/v1/devices/me/reputation/classify", encoded
            ),
        },
        content=encoded,
    )
    assert classified.status_code == 200, classified.text
    assert classified.json() == {
        "identifier": "unknown.example",
        "verdict": "UNKNOWN",
        "state": "RESOLVED",
        "reason": "NO_CURATED_VERDICT",
    }

    # The first real, minimized identifier produces a signed bundle. No example
    # domain or test fixture is ever presented to a child device in production.
    synced = await client.get(
        "/v1/devices/me/reputation?version=0",
        headers={"Authorization": f"Bearer {paired_device.device_token}"},
    )
    bundle = synced.json()["bundle"]
    assert bundle["entries"] == [
        {
            "target_kind": "DOMAIN",
            "identifier": "unknown.example",
            "verdict": "UNKNOWN",
            "source": "guardian-no-curated-verdict",
            "rationale": "No curated verdict is available; no score or heuristic was fabricated.",
            "expires_at": bundle["entries"][0]["expires_at"],
            "bundle_version": 1,
        }
    ]
    assert verify_signed_reputation(
        bundle,
        {
            "test-key": __import__("base64").b64encode(
                Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
                .public_key()
                .public_bytes(Encoding.Raw, PublicFormat.Raw)
            ).decode("ascii")
        },
    )


@pytest.mark.asyncio
async def test_classification_rejects_full_urls_and_parent_reads_server_state(
    client, parent_a, paired_device
) -> None:
    body = {"identifier": "https://unknown.example/path?query=1"}
    encoded = json.dumps(body, separators=(",", ":")).encode()
    rejected = await client.post(
        "/v1/devices/me/reputation/classify",
        headers={
            "Authorization": f"Bearer {paired_device.device_token}",
            **paired_device.signed_headers(
                "/v1/devices/me/reputation/classify", encoded
            ),
        },
        content=encoded,
    )
    assert rejected.status_code == 422, rejected.text

    valid_body = json.dumps({"identifier": "unknown.example"}, separators=(",", ":")).encode()
    classified = await client.post(
        "/v1/devices/me/reputation/classify",
        headers={
            "Authorization": f"Bearer {paired_device.device_token}",
            **paired_device.signed_headers(
                "/v1/devices/me/reputation/classify", valid_body
            ),
        },
        content=valid_body,
    )
    assert classified.status_code == 200, classified.text

    inventory = await client.get(
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}/reputation",
        headers={"Authorization": f"Bearer {parent_a.token}"},
    )
    assert inventory.status_code == 200, inventory.text
    assert any(
        item["identifier"] == "unknown.example" and item["verdict"] == "UNKNOWN"
        for item in inventory.json()["entries"]
    )


@pytest.mark.asyncio
async def test_reputation_full_fallback_does_not_duplicate_current_revision(
    client, parent_a, paired_device
) -> None:
    for identifier in ("one.example", "two.example", "three.example"):
        body = json.dumps({"identifier": identifier}, separators=(",", ":")).encode()
        classified = await client.post(
            "/v1/devices/me/reputation/classify",
            headers={
                "Authorization": f"Bearer {paired_device.device_token}",
                **paired_device.signed_headers(
                    "/v1/devices/me/reputation/classify", body
                ),
            },
            content=body,
        )
        assert classified.status_code == 200, classified.text

    response = await client.get(
        "/v1/devices/me/reputation?version=0",
        headers={"Authorization": f"Bearer {paired_device.device_token}"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["bundle"]["kind"] == "FULL"
    assert payload["bundle"]["bundle_version"] == payload["current_version"]
    assert payload["deltas"] == []
