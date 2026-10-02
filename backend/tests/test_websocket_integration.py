# ruff: noqa: E501
import asyncio
import json
from uuid import UUID

import pytest

from app.api.app import app
from app.events.broadcaster import broadcaster


async def connect(family_id: str, token: str, child_id: str | None):
    incoming: asyncio.Queue[dict[str, object]] = asyncio.Queue()
    outgoing: asyncio.Queue[dict[str, object]] = asyncio.Queue()
    query = f"family_id={family_id}"
    if child_id is not None:
        query += f"&child_profile_id={child_id}"
    scope = {
        "type": "websocket",
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "http_version": "1.1",
        "scheme": "ws",
        "path": "/v1/ws/sync",
        "raw_path": b"/v1/ws/sync",
        "query_string": query.encode(),
        "headers": [(b"authorization", f"Bearer {token}".encode()), (b"host", b"test")],
        "client": ("127.0.0.1", 1234),
        "server": ("test", 80),
        "subprotocols": [],
    }

    async def receive():
        return await incoming.get()

    async def send(message):
        await outgoing.put(message)

    task = asyncio.create_task(app(scope, receive, send))
    await incoming.put({"type": "websocket.connect"})
    return task, incoming, outgoing


async def receive_json(outgoing: asyncio.Queue[dict[str, object]]) -> dict[str, object]:
    message = await asyncio.wait_for(outgoing.get(), timeout=2)
    if message["type"] == "websocket.accept":
        message = await asyncio.wait_for(outgoing.get(), timeout=2)
    assert message["type"] == "websocket.send"
    return json.loads(str(message["text"]))


@pytest.mark.asyncio
async def test_parent_websocket_receives_every_published_event_type(client, parent_a, parent_b) -> None:
    task, incoming, outgoing = await connect(parent_a.family_id, parent_a.token, parent_a.child_id)
    assert (await receive_json(outgoing))["type"] == "catch-up"
    await asyncio.sleep(0)
    for event_type in (
        "policy-version-changed",
        "request-created",
        "request-decided",
        "protection-health-changed",
        "device-status",
    ):
        broadcaster.publish(UUID(parent_a.family_id), {"type": event_type}, UUID(parent_a.child_id))
        assert (await receive_json(outgoing))["type"] == event_type
    broadcaster.publish(UUID(parent_b.family_id), {"type": "device-status"}, UUID(parent_b.child_id))
    assert outgoing.empty()
    await incoming.put({"type": "websocket.disconnect", "code": 1000})
    await task


@pytest.mark.asyncio
async def test_device_websocket_is_child_scoped_and_rejects_other_family(client, paired_device, parent_b) -> None:
    second_child = await client.post(
        f"/v1/families/{paired_device.parent.family_id}/children",
        json={"name": "Casey", "date_of_birth": "2014-08-15", "timezone": "UTC"},
        headers={"Authorization": f"Bearer {paired_device.parent.token}"},
    )
    assert second_child.status_code == 201, second_child.text
    second_child_id = UUID(second_child.json()["id"])
    task, incoming, outgoing = await connect(
        paired_device.parent.family_id,
        paired_device.device_token,
        None,
    )
    assert (await receive_json(outgoing))["type"] == "catch-up"
    await asyncio.sleep(0)
    broadcaster.publish(
        UUID(paired_device.parent.family_id),
        {"type": "request-created"},
        UUID(paired_device.parent.child_id),
    )
    assert (await receive_json(outgoing))["type"] == "request-created"
    # Omitting child_profile_id on a device connection must still be scoped to
    # the child bound to the credential, never the whole family.
    broadcaster.publish(
        UUID(paired_device.parent.family_id),
        {"type": "other-child-event"},
        second_child_id,
    )
    await asyncio.sleep(0)
    assert outgoing.empty()
    await incoming.put({"type": "websocket.disconnect", "code": 1000})
    await task

    denied_task, _, denied_outgoing = await connect(
        parent_b.family_id,
        paired_device.device_token,
        parent_b.child_id,
    )
    await asyncio.wait_for(denied_outgoing.get(), timeout=2)
    denied = await asyncio.wait_for(denied_outgoing.get(), timeout=2)
    assert denied == {"type": "websocket.close", "code": 1008, "reason": ""}
    await denied_task


@pytest.mark.asyncio
async def test_websocket_authentication_failure_is_rejected(client, parent_a) -> None:
    task, _, outgoing = await connect(parent_a.family_id, "invalid", None)
    await asyncio.wait_for(outgoing.get(), timeout=2)
    denied = await asyncio.wait_for(outgoing.get(), timeout=2)
    assert denied == {"type": "websocket.close", "code": 1008, "reason": ""}
    await task
