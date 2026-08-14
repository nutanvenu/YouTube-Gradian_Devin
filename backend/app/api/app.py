import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.models import Parent
from ..auth.service import (
    consume_one_time_token,
    hash_password,
    issue_one_time_token,
    issue_tokens,
    parent_from_access,
    rotate_refresh,
    verify_password,
)
from ..children.models import ChildProfile
from ..core.db import get_session
from ..core.errors import internal_error_handler, validation_error_handler
from ..core.idempotency import payload_hash, replay_or_conflict, save_result
from ..core.notifier import LoggingNotifier
from ..core.rate_limit import InProcessRateLimiter
from ..devices.models import Device, DeviceCredential
from ..devices.service import current_device
from ..families.models import Family, FamilyGuardian, GuardianInvitation, GuardianRole
from ..pairing.models import PairingSession
from ..policies.service import age_band_for_dob, default_policy, validate_timezone
from .schemas import (
    ChildCreate,
    ChildOut,
    ChildUpdate,
    DeviceAckIn,
    DeviceCredentialOut,
    DeviceHeartbeatIn,
    EventBatchIn,
    FamilyCreate,
    FamilyOut,
    GuardianAcceptIn,
    GuardianInviteIn,
    GuardianOut,
    LoginIn,
    PairingOut,
    PairingRedeemIn,
    ParentOut,
    PasswordResetConfirmIn,
    RefreshIn,
    SignupIn,
    TokenConfirmIn,
    TokenRequestIn,
    TokensOut,
)

app = FastAPI(title="Guardian API", version="0.1.0")
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, internal_error_handler)
oauth2 = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")
auth_rate_limiter = InProcessRateLimiter()
notifier = LoggingNotifier()


async def current_parent(
    token: str = Depends(oauth2), session: AsyncSession = Depends(get_session)
) -> Parent:
    return await parent_from_access(session, token)


async def family_for_parent(session: AsyncSession, parent: Parent, family_id: UUID) -> Family:
    family = await session.scalar(
        select(Family)
        .join(FamilyGuardian)
        .where(Family.id == family_id, FamilyGuardian.parent_id == parent.id)
    )
    if family is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Family not found")
    return family


@app.post("/v1/auth/signup", response_model=TokensOut, status_code=201)
async def signup(body: SignupIn, session: AsyncSession = Depends(get_session)) -> TokensOut:
    auth_rate_limiter.check(f"signup:{body.email.lower()}", 5, 60)
    if await session.scalar(select(Parent).where(Parent.email == body.email.lower())) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    parent = Parent(email=body.email.lower(), password_hash=hash_password(body.password))
    session.add(parent)
    await session.flush()
    access, refresh = await issue_tokens(session, parent)
    await session.commit()
    return TokensOut(access_token=access, refresh_token=refresh)


@app.post("/v1/auth/login", response_model=TokensOut)
async def login(body: LoginIn, session: AsyncSession = Depends(get_session)) -> TokensOut:
    auth_rate_limiter.check(f"login:{body.email.lower()}", 10, 60)
    parent = await session.scalar(select(Parent).where(Parent.email == body.email.lower()))
    if parent is None or not verify_password(body.password, parent.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    access, refresh = await issue_tokens(session, parent)
    await session.commit()
    return TokensOut(access_token=access, refresh_token=refresh)


@app.post("/v1/auth/refresh", response_model=TokensOut)
async def refresh(body: RefreshIn, session: AsyncSession = Depends(get_session)) -> TokensOut:
    auth_rate_limiter.check("refresh", 30, 60)
    access, refresh_token = await rotate_refresh(session, body.refresh_token)
    return TokensOut(access_token=access, refresh_token=refresh_token)


@app.get("/v1/auth/me", response_model=ParentOut)
async def me(parent: Parent = Depends(current_parent)) -> Parent:
    return parent


@app.post("/v1/auth/verification/request", status_code=202)
async def request_verification(
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> None:
    token = await issue_one_time_token(session, parent, "EMAIL_VERIFY", timedelta(hours=24))
    await notifier.send_email(parent.email, "Verify your Guardian email", token)
    await session.commit()


@app.post("/v1/auth/verification/confirm", status_code=204)
async def confirm_verification(
    body: TokenConfirmIn, session: AsyncSession = Depends(get_session)
) -> None:
    parent = await consume_one_time_token(session, body.token, "EMAIL_VERIFY")
    parent.email_verified_at = datetime.now(UTC)
    await session.commit()


@app.post("/v1/auth/password-reset/request", status_code=202)
async def request_password_reset(
    body: TokenRequestIn, session: AsyncSession = Depends(get_session)
) -> None:
    parent = await session.scalar(select(Parent).where(Parent.email == body.email.lower()))
    if parent is not None:
        token = await issue_one_time_token(session, parent, "PASSWORD_RESET", timedelta(hours=1))
        await notifier.send_email(parent.email, "Reset your Guardian password", token)
        await session.commit()


@app.post("/v1/auth/password-reset/confirm", status_code=204)
async def confirm_password_reset(
    body: PasswordResetConfirmIn, session: AsyncSession = Depends(get_session)
) -> None:
    parent = await consume_one_time_token(session, body.token, "PASSWORD_RESET")
    parent.password_hash = hash_password(body.password)
    await session.commit()


@app.post("/v1/auth/logout", status_code=204)
async def logout(body: RefreshIn, session: AsyncSession = Depends(get_session)) -> None:
    auth_rate_limiter.check("logout", 30, 60)
    from ..auth.service import revoke_refresh

    await revoke_refresh(session, body.refresh_token)


@app.post("/v1/families", response_model=FamilyOut, status_code=201)
async def create_family(
    body: FamilyCreate,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> Family:
    family = Family(name=body.name)
    session.add(family)
    await session.flush()
    session.add(FamilyGuardian(family_id=family.id, parent_id=parent.id, role=GuardianRole.OWNER))
    await session.commit()
    return family


@app.get("/v1/families/{family_id}", response_model=FamilyOut)
async def read_family(
    family_id: UUID,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> Family:
    return await family_for_parent(session, parent, family_id)


@app.post("/v1/families/{family_id}/children", response_model=ChildOut, status_code=201)
async def create_child(
    family_id: UUID,
    body: ChildCreate,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> ChildProfile:
    await family_for_parent(session, parent, family_id)
    timezone = validate_timezone(body.timezone)
    band = age_band_for_dob(body.date_of_birth)
    child = ChildProfile(
        family_id=family_id,
        name=body.name,
        date_of_birth=body.date_of_birth,
        age_band=band,
        timezone=timezone,
        policy_document={},
    )
    session.add(child)
    await session.flush()
    child.policy_document = default_policy(family_id, child.id, band, timezone)
    await session.commit()
    await session.refresh(child)
    return child


@app.get("/v1/families/{family_id}/children", response_model=list[ChildOut])
async def list_children(
    family_id: UUID,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> list[ChildProfile]:
    await family_for_parent(session, parent, family_id)
    return list(
        (
            await session.scalars(select(ChildProfile).where(ChildProfile.family_id == family_id))
        ).all()
    )


@app.get("/v1/families/{family_id}/children/{child_id}", response_model=ChildOut)
async def read_child(
    family_id: UUID,
    child_id: UUID,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> ChildProfile:
    await family_for_parent(session, parent, family_id)
    child = await session.scalar(
        select(ChildProfile).where(ChildProfile.id == child_id, ChildProfile.family_id == family_id)
    )
    if child is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Child not found")
    return child


@app.patch("/v1/families/{family_id}/children/{child_id}", response_model=ChildOut)
async def update_child(
    family_id: UUID,
    child_id: UUID,
    body: ChildUpdate,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> ChildProfile:
    child = await read_child(family_id, child_id, parent, session)
    changes = body.model_dump(exclude_unset=True)
    if "timezone" in changes:
        changes["timezone"] = validate_timezone(str(changes["timezone"]))
    for key, value in changes.items():
        setattr(child, key, value)
    if "date_of_birth" in changes:
        child.age_band = age_band_for_dob(child.date_of_birth)
        child.policy_document = default_policy(family_id, child.id, child.age_band, child.timezone)
    await session.commit()
    await session.refresh(child)
    return child


@app.delete("/v1/families/{family_id}/children/{child_id}", status_code=204)
async def delete_child(
    family_id: UUID,
    child_id: UUID,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> None:
    child = await read_child(family_id, child_id, parent, session)
    await session.delete(child)
    await session.commit()


@app.get("/v1/families/{family_id}/guardians", response_model=list[GuardianOut])
async def list_guardians(
    family_id: UUID,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> list[FamilyGuardian]:
    await family_for_parent(session, parent, family_id)
    return list(
        (
            await session.scalars(
                select(FamilyGuardian).where(FamilyGuardian.family_id == family_id)
            )
        ).all()
    )


@app.post("/v1/families/{family_id}/guardians/invite", status_code=202)
async def invite_guardian(
    family_id: UUID,
    body: GuardianInviteIn,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> None:
    await family_for_parent(session, parent, family_id)
    auth_rate_limiter.check(f"guardian-invite:{parent.id}", 5, 60)
    raw = secrets.token_urlsafe(32)
    invitation = GuardianInvitation(
        family_id=family_id,
        email=body.email.lower(),
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.add(invitation)
    await notifier.send_email(body.email, "Join a Guardian family", raw)
    await session.commit()


@app.post("/v1/families/guardians/accept", status_code=204)
async def accept_guardian(
    body: GuardianAcceptIn,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> None:
    auth_rate_limiter.check(f"guardian-accept:{parent.id}", 10, 60)
    invitation = await session.scalar(
        select(GuardianInvitation).where(
            GuardianInvitation.token_hash == hashlib.sha256(body.token.encode()).hexdigest()
        )
    )
    if (
        invitation is None
        or invitation.accepted_at is not None
        or invitation.expires_at <= datetime.now(UTC)
        or invitation.email != parent.email
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invitation is invalid")
    invitation.accepted_at = datetime.now(UTC)
    session.add(
        FamilyGuardian(
            family_id=invitation.family_id,
            parent_id=parent.id,
            role=GuardianRole.CO_GUARDIAN,
        )
    )
    await session.commit()


@app.post(
    "/v1/families/{family_id}/children/{child_id}/pairing",
    response_model=PairingOut,
)
async def create_pairing(
    family_id: UUID,
    child_id: UUID,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> PairingOut:
    auth_rate_limiter.check(f"pairing:create:{parent.id}", 10, 60)
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
        qr_payload=f"guardian://pair/{row.id}?code={code}",
        expires_at=row.expires_at,
    )


@app.post("/v1/devices/pair", response_model=DeviceCredentialOut)
async def redeem_pairing(
    body: PairingRedeemIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> DeviceCredentialOut:
    digest = payload_hash(body.model_dump(mode="json"))
    if idempotency_key is not None:
        replay = await replay_or_conflict(session, "pairing_redeem", idempotency_key, digest)
        if replay is not None:
            return DeviceCredentialOut.model_validate(replay.response_body)
    auth_rate_limiter.check(f"pairing:redeem:{body.session_id}", 10, 60)
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
    result = DeviceCredentialOut(device_id=device.id, device_token=raw)
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


@app.post("/v1/families/{family_id}/devices/{device_id}/revoke", status_code=204)
async def revoke_device(
    family_id: UUID,
    device_id: UUID,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> None:
    await family_for_parent(session, parent, family_id)
    device = await session.scalar(
        select(Device)
        .join(ChildProfile, ChildProfile.id == Device.child_profile_id)
        .where(Device.id == device_id, ChildProfile.family_id == family_id)
    )
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")
    now = datetime.now(UTC)
    device.revoked_at = now
    credential = await session.scalar(
        select(DeviceCredential).where(DeviceCredential.device_id == device.id)
    )
    if credential is not None:
        credential.revoked_at = now
    await session.commit()


@app.get("/v1/devices/me/policy")
async def fetch_policy(
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    child = await session.get(ChildProfile, device.child_profile_id)
    if child is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Child not found")
    return child.policy_document


@app.post("/v1/devices/me/policy/ack", status_code=204)
async def acknowledge_policy(
    body: DeviceAckIn,
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> None:
    device.policy_version_applied = body.policy_version
    await session.commit()


@app.post("/v1/devices/me/heartbeat", status_code=204)
async def heartbeat(
    body: DeviceHeartbeatIn,
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> None:
    device.protection_state = body.protection_state
    device.capabilities = body.capabilities
    device.last_seen_at = datetime.now(UTC)
    await session.commit()


@app.post("/v1/devices/me/events", status_code=202)
async def ingest_events(
    body: EventBatchIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> None:
    digest = payload_hash(body.model_dump(mode="json"))
    if idempotency_key is not None:
        replay = await replay_or_conflict(session, "event_batch", idempotency_key, digest)
        if replay is not None:
            return
    device.last_seen_at = datetime.now(UTC)
    if idempotency_key is not None:
        await save_result(session, "event_batch", idempotency_key, digest, 202, {})
    await session.commit()
