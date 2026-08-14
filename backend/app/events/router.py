# ruff: noqa: E501
from fastapi import APIRouter

from ..api.handler_support import (
    UUID,
    AsyncSession,
    ChildProfile,
    Depends,
    Device,
    DeviceCredential,
    FamilyGuardian,
    HTTPException,
    PolicyBundle,
    WebSocket,
    WebSocketDisconnect,
    asyncio,
    broadcaster,
    get_session,
    hashlib,
    parent_from_access,
    select,
)

router = APIRouter()


async def websocket_sync(
    websocket: WebSocket,
    session: AsyncSession = Depends(get_session),
) -> None:
    await websocket.accept()
    token = websocket.headers.get("authorization", "")
    if token.lower().startswith("bearer "):
        token = token[7:]
    family_id = websocket.query_params.get("family_id")
    child_id = websocket.query_params.get("child_profile_id")
    if not token or not family_id:
        await websocket.close(code=1008)
        return
    try:
        family_uuid = UUID(family_id)
    except ValueError:
        await websocket.close(code=1008)
        return
    parent = None
    try:
        parent = await parent_from_access(session, token)
    except HTTPException:
        pass
    device = None
    if parent is None:
        digest = hashlib.sha256(token.encode()).hexdigest()
        credential = await session.scalar(
            select(DeviceCredential).where(
                DeviceCredential.token_hash == digest,
                DeviceCredential.revoked_at.is_(None),
            )
        )
        if credential is not None:
            device = await session.get(Device, credential.device_id)
    if parent is None and (device is None or device.revoked_at is not None):
        await websocket.close(code=1008)
        return
    if parent is not None:
        allowed = await session.scalar(
            select(FamilyGuardian).where(
                FamilyGuardian.family_id == family_uuid,
                FamilyGuardian.parent_id == parent.id,
            )
        )
        if allowed is None:
            await websocket.close(code=1008)
            return
    else:
        assert device is not None
        child = await session.scalar(
            select(ChildProfile).where(
                ChildProfile.id == device.child_profile_id,
                ChildProfile.family_id == family_uuid,
            )
        )
        if child is None or (child_id is not None and str(child.id) != child_id):
            await websocket.close(code=1008)
            return
    bundle = None
    if child_id is not None:
        try:
            child_uuid = UUID(child_id)
        except ValueError:
            await websocket.close(code=1008)
            return
        child = await session.scalar(
            select(ChildProfile).where(
                ChildProfile.id == child_uuid, ChildProfile.family_id == family_uuid
            )
        )
        if child is None:
            await websocket.close(code=1008)
            return
        bundle = await session.scalar(
            select(PolicyBundle).where(
                PolicyBundle.child_profile_id == child_uuid,
                PolicyBundle.is_current.is_(True),
            )
        )
    await websocket.send_json(
        {
            "type": "catch-up",
            "policy_version": bundle.policy_version if bundle is not None else None,
            "open_requests": [],
        }
    )
    connection = broadcaster.subscribe(family_uuid, child_uuid if child_id is not None else None)
    try:
        while True:
            receive_task = asyncio.create_task(websocket.receive_text())
            event_task = asyncio.create_task(connection.queue.get())
            done, pending = await asyncio.wait(
                {receive_task, event_task},
                timeout=30,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            if not done:
                await websocket.send_json({"type": "ping"})
                continue
            if event_task in done:
                await websocket.send_json(event_task.result())
                continue
            message = receive_task.result()
            if message != "pong":
                await websocket.send_json({"type": "pong"})
    except (WebSocketDisconnect, TimeoutError):
        return
    finally:
        broadcaster.unsubscribe(connection)

router.add_api_websocket_route('/v1/ws/sync', websocket_sync)
