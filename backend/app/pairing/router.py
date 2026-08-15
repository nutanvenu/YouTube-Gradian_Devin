# ruff: noqa: E501
from fastapi import APIRouter

from ..api.handler_support import (
    UTC,
    UUID,
    AsyncSession,
    Base64Error,
    ChildProfile,
    Depends,
    Device,
    DeviceCredential,
    DeviceCredentialOut,
    Ed25519PublicKey,
    Header,
    HTTPException,
    HTTPRequest,
    PairingOut,
    PairingRedeemIn,
    PairingSession,
    Parent,
    auth_rate_limiter,
    base64,
    current_parent,
    datetime,
    get_session,
    hashlib,
    payload_hash,
    rate_key,
    replay_or_conflict,
    save_result,
    secrets,
    select,
    status,
    timedelta,
)
from ..children.router import read_child

router = APIRouter()


async def create_pairing(
    family_id: UUID,
    child_id: UUID,
    request: HTTPRequest,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> PairingOut:
    auth_rate_limiter.check(rate_key(request, "pairing-create", str(parent.id)), 10, 60)
    await read_child(family_id, child_id, parent, session)
    code = f"{secrets.randbelow(1_000_000):06d}"
    row = PairingSession(
        child_profile_id=child_id,
        code_hash=hashlib.sha256(code.encode()).hexdigest(),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    session.add(row)
    await session.commit()
    return PairingOut(
        session_id=row.id,
        code=code,
        qr_payload=f"guardian://pair/{row.id}?child_id={child_id}&code={code}",
        expires_at=row.expires_at,
    )

async def redeem_pairing(
    body: PairingRedeemIn,
    request: HTTPRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> DeviceCredentialOut:
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(body.public_key, validate=True))
    except (ValueError, Base64Error):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Device public key is invalid") from None
    digest = payload_hash(body.model_dump(mode="json"))
    if idempotency_key is not None:
        replay = await replay_or_conflict(session, "pairing_redeem", idempotency_key, digest)
        if replay is not None:
            return DeviceCredentialOut.model_validate(replay.response_body)
    auth_rate_limiter.check(rate_key(request, "pairing-redeem", str(body.session_id)), 10, 60)
    row = await session.scalar(select(PairingSession).where(PairingSession.id == body.session_id))
    valid = False
    if row is not None:
        valid = (
            row.child_profile_id == body.child_profile_id
            and row.redeemed_at is None
            and row.expires_at > datetime.now(UTC)
            and row.attempts < 5
            and secrets.compare_digest(
                row.code_hash, hashlib.sha256(body.code.encode()).hexdigest()
            )
        )
    if not valid:
        if row is not None:
            row.attempts += 1
            await session.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pairing code is invalid")
    assert row is not None
    row.redeemed_at = datetime.now(UTC)
    device = Device(
        child_profile_id=body.child_profile_id,
        platform=body.platform,
        public_key=body.public_key,
        capabilities={},
    )
    session.add(device)
    await session.flush()
    raw = secrets.token_urlsafe(48)
    session.add(
        DeviceCredential(
            device_id=device.id,
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        )
    )
    child = await session.get(ChildProfile, body.child_profile_id)
    assert child is not None
    result = DeviceCredentialOut(
        device_id=device.id,
        device_token=raw,
        family_id=child.family_id,
    )
    if idempotency_key is not None:
        await save_result(
            session,
            "pairing_redeem",
            idempotency_key,
            digest,
            status.HTTP_200_OK,
            result.model_dump(mode="json"),
        )
    await session.commit()
    return result

router.add_api_route("/v1/families/{family_id}/children/{child_id}/pairing", create_pairing, methods=["POST"], response_model=None)
router.add_api_route("/v1/devices/pair", redeem_pairing, methods=["POST"], response_model=None)
