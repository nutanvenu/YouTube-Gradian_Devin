import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select

from app.api.handler_support import FamilyGuardian, PolicyBundle, PushAction
from app.devices import router as device_router


class CapturePushSender:
    def __init__(self) -> None:
        self.deliveries: list[tuple[object, dict[str, object]]] = []

    async def send(self, recipient, payload: dict[str, object]) -> None:
        self.deliveries.append((recipient, payload))


@pytest.mark.asyncio
async def test_request_push_actions_are_real_idempotent_and_authorized(
    client, parent_a, paired_device, database_session, monkeypatch
) -> None:
    sender = CapturePushSender()
    monkeypatch.setattr(device_router, "push_sender", sender)
    parent_headers = {"Authorization": f"Bearer {parent_a.token}"}
    registered = await client.post(
        "/v1/me/push-tokens",
        headers=parent_headers,
        json={"platform": "ANDROID", "token": "parent-device-token-123456789"},
    )
    assert registered.status_code == 204

    # A blank MORE_TIME subject is an explicit device-wide request. A display
    # label such as "Chrome" must never be widened to this device grant.
    payload = {"request_type": "MORE_TIME", "subject": None, "reason": "Homework"}
    body = json.dumps(payload, separators=(",", ":")).encode()
    path = "/v1/devices/me/requests"
    response = await client.post(
        path,
        content=body,
        headers={
            **paired_device.signed_headers(path, body),
            "Content-Type": "application/json",
            "Idempotency-Key": "push-action-request-1",
        },
    )
    assert response.status_code == 201, response.text
    assert len(sender.deliveries) == 1
    notification = sender.deliveries[0][1]
    assert notification["type"] == "REQUEST_DECISION"
    actions = notification["actions"]
    assert isinstance(actions, list)
    approve_path = actions[0]["path"]
    deny_path = actions[1]["path"]
    assert approve_path.endswith("/approve")
    assert deny_path.endswith("/deny")

    approved = await client.post(approve_path, json={})
    assert approved.status_code == 200
    assert approved.json()["state"] == "APPROVED"
    current_bundle = await database_session.scalar(
        select(PolicyBundle).where(
            PolicyBundle.child_profile_id == paired_device.parent.child_id,
            PolicyBundle.is_current.is_(True),
        )
    )
    assert current_bundle is not None
    assert current_bundle.new_value["temporary_overrides"][-1]["target_kind"] == "DEVICE"
    assert current_bundle.new_value["temporary_overrides"][-1]["target_ref"] == "device"
    assert current_bundle.new_value["temporary_overrides"][-1]["daily_minutes"] == 195
    repeated = await client.post(approve_path, json={})
    assert repeated.status_code == 200
    assert repeated.json()["state"] == "APPROVED"
    opposite = await client.post(deny_path, json={})
    assert opposite.status_code == 409
    invalid = await client.post("/v1/push/actions/not-a-token/approve", json={})
    assert invalid.status_code == 404

    expired_body = json.dumps(
        {"request_type": "UNBLOCK_SITE", "subject": "example.org", "reason": "Study"},
        separators=(",", ":"),
    ).encode()
    expired_response = await client.post(
        path,
        content=expired_body,
        headers={
            **paired_device.signed_headers(path, expired_body),
            "Content-Type": "application/json",
            "Idempotency-Key": "push-action-request-2",
        },
    )
    assert expired_response.status_code == 201
    expired_payload = sender.deliveries[-1][1]
    expired_path = expired_payload["actions"][0]["path"]
    token = expired_path.split("/actions/", 1)[1].rsplit("/", 1)[0]
    action = await database_session.scalar(
        select(PushAction).where(
            PushAction.token_hash == hashlib.sha256(token.encode()).hexdigest()
        )
    )
    assert action is not None
    action.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await database_session.commit()
    expired = await client.post(expired_path, json={})
    assert expired.status_code == 410


@pytest.mark.asyncio
async def test_more_time_approval_targets_app_and_domain_grants(
    client, paired_device, database_session
) -> None:
    parent_headers = {"Authorization": f"Bearer {paired_device.parent.token}"}
    limited = await client.post(
        f"/v1/families/{paired_device.parent.family_id}/children/{paired_device.parent.child_id}/policy/mutations",
        headers=parent_headers,
        json={"operation": "APP_DAILY_MINUTES", "target": "com.example.chrome", "value": 30},
    )
    assert limited.status_code == 200, limited.text

    async def create_request(subject: str, key: str) -> str:
        body = json.dumps(
            {"request_type": "MORE_TIME", "subject": subject, "reason": "Homework"},
            separators=(",", ":"),
        ).encode()
        path = "/v1/devices/me/requests"
        response = await client.post(
            path,
            content=body,
            headers={
                **paired_device.signed_headers(path, body),
                "Content-Type": "application/json",
                "Idempotency-Key": key,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    app_request_id = await create_request("com.example.chrome", "more-time-app")
    app_approved = await client.post(
        f"/v1/families/{paired_device.parent.family_id}/requests/{app_request_id}/approve",
        headers=parent_headers,
        json={"reason": "Approved for homework"},
    )
    assert app_approved.status_code == 200, app_approved.text
    current_bundle = await database_session.scalar(
        select(PolicyBundle).where(
            PolicyBundle.child_profile_id == paired_device.parent.child_id,
            PolicyBundle.is_current.is_(True),
        )
    )
    assert current_bundle is not None
    app_override = current_bundle.new_value["temporary_overrides"][-1]
    assert app_override["target_kind"] == "APP"
    assert app_override["target_ref"] == "com.example.chrome"
    assert app_override["action"] == "LIMIT"
    assert app_override["daily_minutes"] == 45

    domain_request_id = await create_request("EXAMPLE.COM.", "more-time-domain")
    domain_approved = await client.post(
        f"/v1/families/{paired_device.parent.family_id}/requests/{domain_request_id}/approve",
        headers=parent_headers,
        json={"reason": "Approved for research"},
    )
    assert domain_approved.status_code == 200, domain_approved.text
    current_bundle = await database_session.scalar(
        select(PolicyBundle).where(
            PolicyBundle.child_profile_id == paired_device.parent.child_id,
            PolicyBundle.is_current.is_(True),
        )
    )
    assert current_bundle is not None
    domain_override = current_bundle.new_value["temporary_overrides"][-1]
    assert domain_override["target_kind"] == "DOMAIN"
    assert domain_override["target_ref"] == "example.com"
    assert domain_override["action"] == "ALLOW"
    assert "daily_minutes" not in domain_override


@pytest.mark.asyncio
async def test_push_action_rejects_revoked_parent_and_skips_unregistered_delivery(
    client, parent_a, paired_device, database_session, monkeypatch
) -> None:
    sender = CapturePushSender()
    monkeypatch.setattr(device_router, "push_sender", sender)
    headers = {"Authorization": f"Bearer {parent_a.token}"}
    registered = await client.post(
        "/v1/me/push-tokens",
        headers=headers,
        json={"platform": "ANDROID", "token": "parent-device-token-revoked"},
    )
    assert registered.status_code == 204
    payload = {"request_type": "UNBLOCK_APP", "subject": "Chrome", "reason": "Homework"}
    body = json.dumps(payload, separators=(",", ":")).encode()
    path = "/v1/devices/me/requests"
    response = await client.post(
        path,
        content=body,
        headers={
            **paired_device.signed_headers(path, body),
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 201
    action_path = sender.deliveries[0][1]["actions"][0]["path"]
    parent = await client.get("/v1/auth/me", headers=headers)
    assert parent.status_code == 200

    await database_session.execute(
        delete(FamilyGuardian).where(
            FamilyGuardian.family_id == parent_a.family_id,
            FamilyGuardian.parent_id == parent.json()["id"],
        )
    )
    await database_session.commit()
    rejected = await client.post(action_path, json={})
    assert rejected.status_code == 403


@pytest.mark.asyncio
async def test_request_without_active_parent_push_registration_has_no_delivery(
    client, paired_device, monkeypatch
) -> None:
    sender = CapturePushSender()
    monkeypatch.setattr(device_router, "push_sender", sender)
    payload = {"request_type": "UNBLOCK_APP", "subject": "Chrome", "reason": "Homework"}
    body = json.dumps(payload, separators=(",", ":")).encode()
    path = "/v1/devices/me/requests"
    response = await client.post(
        path,
        content=body,
        headers={
            **paired_device.signed_headers(path, body),
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 201
    assert sender.deliveries == []
