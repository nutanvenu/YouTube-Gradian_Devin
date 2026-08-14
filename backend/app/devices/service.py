import base64
import hashlib
import time
from binascii import Error as Base64Error
from datetime import UTC, datetime, timedelta
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.db import get_session
from ..core.models import DeviceRequestNonce
from .models import Device, DeviceCredential

bearer = HTTPBearer()
DEVICE_PROOF_FRESHNESS_SECONDS = 300


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


def device_request_message(
    method: str, path: str, timestamp: str, nonce: str, body: bytes
) -> bytes:
    digest = hashlib.sha256(body).hexdigest()
    return f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{digest}".encode()


def verify_device_request(
    public_key: bytes,
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body: bytes,
    signature: str,
) -> bool:
    try:
        if (
            abs(int(time.time()) - int(timestamp)) > DEVICE_PROOF_FRESHNESS_SECONDS
            or len(nonce) < 16
        ):
            return False
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            base64.b64decode(signature, validate=True),
            device_request_message(method, path, timestamp, nonce, body),
        )
        return True
    except (ValueError, TypeError, Base64Error, InvalidSignature):
        return False


async def verify_device_request_headers(
    request: Request, device: Device, session: AsyncSession
) -> None:
    timestamp = request.headers.get("X-Guardian-Device-Timestamp")
    nonce = request.headers.get("X-Guardian-Device-Nonce")
    signature = request.headers.get("X-Guardian-Device-Signature")
    if not timestamp or not nonce or not signature:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Device proof is required")
    try:
        public_key = base64.b64decode(device.public_key, validate=True)
    except (ValueError, Base64Error):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid device proof") from None
    if not verify_device_request(
        public_key,
        request.method,
        request.url.path,
        timestamp,
        nonce,
        await request.body(),
        signature,
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid device proof")
    cutoff = datetime.now(UTC) - timedelta(seconds=DEVICE_PROOF_FRESHNESS_SECONDS)
    await session.execute(
        delete(DeviceRequestNonce).where(
            DeviceRequestNonce.device_id == device.id,
            DeviceRequestNonce.created_at < cutoff,
        )
    )
    session.add(DeviceRequestNonce(device_id=device.id, nonce=nonce))
    try:
        await session.flush()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Replayed device proof"
        ) from error
