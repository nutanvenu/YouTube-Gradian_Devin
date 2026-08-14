import hashlib
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.db import get_session
from .models import Device, DeviceCredential

bearer = HTTPBearer()


async def current_device(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> Device:
    digest = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    row = await session.scalar(
        select(DeviceCredential).where(
            DeviceCredential.token_hash == digest,
            DeviceCredential.revoked_at.is_(None),
        )
    )
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid device credentials")
    device = await session.get(Device, row.device_id)
    if device is None or device.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid device credentials")
    return device


async def device_for_child(session: AsyncSession, device_id: UUID) -> Device:
    device = await session.get(Device, device_id)
    if device is None or device.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Device is revoked")
    return device
