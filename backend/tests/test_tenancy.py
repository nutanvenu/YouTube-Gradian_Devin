import json

import pytest
from conftest import ParentFamily


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "suffix", "body"),
    [
        ("get", "", None),
        ("post", "/children", {"name": "Other", "date_of_birth": "2015-01-01", "timezone": "UTC"}),
        ("get", "/children", None),
        ("get", "/guardians", None),
        ("post", "/guardians/invite", {"email": "other@example.com"}),
        ("post", "/children/{child_id}/pairing", None),
        ("patch", "/children/{child_id}", {"name": "Other"}),
        ("delete", "/children/{child_id}", None),
    ],
)
async def test_every_family_route_enforces_tenancy(
    client, parent_a: ParentFamily, parent_b: ParentFamily, method: str, suffix: str, body
) -> None:
    path = f"/v1/families/{parent_a.family_id}{suffix.format(child_id=parent_a.child_id)}"
    response = await client.request(
        method.upper(),
        path,
        json=body,
        headers={"Authorization": f"Bearer {parent_b.token}"},
    )
    assert response.status_code == 404


@pytest.mark.parametrize("action", ["approve", "deny"])
@pytest.mark.parametrize("idempotent", [False, True])
async def test_decision_must_match_url_family_even_for_a_parent_in_both_families(
    client, paired_device, action: str, idempotent: bool
) -> None:
    headers = {"Authorization": f"Bearer {paired_device.parent.token}"}
    other_family = await client.post(
        "/v1/families", json={"name": "Second family"}, headers=headers
    )
    assert other_family.status_code == 201
    path = "/v1/devices/me/requests"
    body = json.dumps({"request_type": "MORE_TIME", "reason": "Homework"}).encode()
    created = await client.post(
        path, content=body, headers=paired_device.signed_headers(path, body)
    )
    assert created.status_code == 201
    request_id = created.json()["id"]
    decision_headers = headers | (
        {"Idempotency-Key": f"decision-{request_id}"} if idempotent else {}
    )
    wrong = await client.post(
        f"/v1/families/{other_family.json()['id']}/requests/{request_id}/{action}",
        headers=decision_headers,
        json={"reason": "Decision"},
    )
    assert wrong.status_code == 404
    pending = await client.get(
        f"/v1/families/{paired_device.parent.family_id}/requests", headers=headers
    )
    assert pending.json()[0]["state"] == "PENDING"
    correct = await client.post(
        f"/v1/families/{paired_device.parent.family_id}/requests/{request_id}/{action}",
        headers=decision_headers,
        json={"reason": "Decision"},
    )
    assert correct.status_code == 200, correct.text
