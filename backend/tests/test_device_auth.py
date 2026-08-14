import base64
import hashlib
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import DeviceRequestNonce
from app.devices.service import device_request_message, verify_device_request


def test_device_request_signature_verifies_canonical_envelope() -> None:
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    timestamp = str(int(time.time()))
    nonce = str(uuid4())
    body = b'{"request_type":"MORE_TIME","subject":null,"reason":null}'
    message = device_request_message("POST", "/v1/devices/me/requests", timestamp, nonce, body)
    signature = base64.b64encode(private.sign(message)).decode("ascii")
    assert verify_device_request(
        public.public_bytes(Encoding.Raw, PublicFormat.Raw),
        "POST",
        "/v1/devices/me/requests",
        timestamp,
        nonce,
        body,
        signature,
    )


def test_device_request_signature_rejects_tampered_body() -> None:
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    timestamp = str(int(time.time()))
    nonce = str(uuid4())
    body = b'{"request_type":"MORE_TIME"}'
    message = device_request_message("POST", "/v1/devices/me/requests", timestamp, nonce, body)
    signature = base64.b64encode(private.sign(message)).decode("ascii")
    assert not verify_device_request(
        public.public_bytes(Encoding.Raw, PublicFormat.Raw),
        "POST",
        "/v1/devices/me/requests",
        timestamp,
        nonce,
        hashlib.sha256(body + b"!").hexdigest(),
        signature,
    )


async def test_device_request_proof_prunes_stale_nonces(
    client: httpx.AsyncClient,
    paired_device,
    database_session: AsyncSession,
) -> None:
    stale = DeviceRequestNonce(
        device_id=UUID(paired_device.device_id),
        nonce="stale-" + str(uuid4()),
        created_at=datetime.now(UTC) - timedelta(seconds=301),
    )
    database_session.add(stale)
    await database_session.commit()
    body = b'{"request_type":"MORE_TIME","subject":null,"reason":"need it"}'
    response = await client.post(
        "/v1/devices/me/requests",
        content=body,
        headers={
            **paired_device.signed_headers("/v1/devices/me/requests", body),
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 201, response.text
    rows = (
        await database_session.scalars(
            select(DeviceRequestNonce).where(DeviceRequestNonce.device_id == stale.device_id)
        )
    ).all()
    assert all(row.nonce != stale.nonce for row in rows)
