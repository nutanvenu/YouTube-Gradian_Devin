import asyncio
import hashlib
import secrets
from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi import Request as HTTPRequest
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.models import Parent
from ..auth.service import (
    DUMMY_PASSWORD_HASH,
    consume_one_time_token,
    hash_password,
    issue_one_time_token,
    issue_tokens,
    parent_from_access,
    revoke_all_refresh,
    revoke_refresh,
    rotate_refresh,
    verify_password,
)
from ..children.models import ChildProfile
from ..core.config import get_settings
from ..core.db import get_session
from ..core.errors import (
    http_exception_handler,
    internal_error_handler,
    validation_error_handler,
)
from ..core.idempotency import payload_hash, replay_or_conflict, save_result
from ..core.notifier import LoggingNotifier
from ..core.rate_limit import InProcessRateLimiter
from ..devices.models import Device, DeviceCredential
from ..devices.service import current_device
from ..events.broadcaster import broadcaster
from ..events.models import (
    ProtectionHealthEvent,
    SafetyEvent,
    UsageAggregate,
    WebEvent,
)
from ..families.models import Family, FamilyGuardian, GuardianInvitation, GuardianRole
from ..pairing.models import PairingSession
from ..policies.models import PolicyBundle
from ..policies.service import (
    age_band_for_dob,
    create_initial_bundle,
    create_next_bundle,
    default_policy,
    validate_timezone,
)
from ..policies.signing import configured_trusted_public_keys, signer
from ..push.models import PushToken
from ..requests.models import Request as RequestRow
from ..requests.models import RequestState
from ..requests.service import is_expired, transition
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
    PolicyMutationIn,
    PushTokenIn,
    RefreshIn,
    RequestCreateIn,
    RequestDecisionIn,
    RequestOut,
    SignupIn,
    TokenConfirmIn,
    TokenRequestIn,
    TokensOut,
)

app = FastAPI(title="Guardian API", version="0.1.0")
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, internal_error_handler)
oauth2 = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")
auth_rate_limiter = InProcessRateLimiter()
notifier = LoggingNotifier()
__all__ = ["app", "notifier", "parent_from_access", "signer"]


def policy_records(policy: dict[str, object], key: str) -> list[dict[str, object]]:
    value = policy.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def policy_mapping(policy: dict[str, object], key: str) -> dict[str, object]:
    value = policy.get(key)
    if not isinstance(value, Mapping):
        raise HTTPException(status.HTTP_409_CONFLICT, "Policy is malformed")
    return dict(value)


@app.get("/v1/policy/public-key")
async def policy_public_key() -> dict[str, object]:
    settings = get_settings()
    trusted = configured_trusted_public_keys()
    if settings.policy_key_id not in trusted:
        trusted[settings.policy_key_id] = signer.public_key()
    return {
        "key_id": settings.policy_key_id,
        "public_key": trusted[settings.policy_key_id],
        "trusted_public_keys": trusted,
    }


def rate_key(request: HTTPRequest, operation: str, principal: str) -> str:
    client_ip = request.client.host if request.client is not None else "unknown"
    return f"{operation}:{client_ip}:{principal}"


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
async def signup(
    body: SignupIn,
    request: HTTPRequest,
    session: AsyncSession = Depends(get_session),
) -> TokensOut:
    auth_rate_limiter.check(rate_key(request, "signup", body.email.lower()), 5, 60)
    if await session.scalar(select(Parent).where(Parent.email == body.email.lower())) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    parent = Parent(email=body.email.lower(), password_hash=hash_password(body.password))
    session.add(parent)
    await session.flush()
    assert isinstance(parent, Parent)
    access, refresh = await issue_tokens(session, parent)
    await session.commit()
    return TokensOut(access_token=access, refresh_token=refresh)


@app.post("/v1/auth/login", response_model=TokensOut)
async def login(
    body: LoginIn,
    request: HTTPRequest,
    session: AsyncSession = Depends(get_session),
) -> TokensOut:
    auth_rate_limiter.check(rate_key(request, "login", body.email.lower()), 10, 60)
    parent = await session.scalar(select(Parent).where(Parent.email == body.email.lower()))
    password_hash = parent.password_hash if parent is not None else DUMMY_PASSWORD_HASH
    password_valid = verify_password(body.password, password_hash)
    if parent is None or not password_valid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    access, refresh = await issue_tokens(session, parent)
    await session.commit()
    return TokensOut(access_token=access, refresh_token=refresh)


@app.post("/v1/auth/refresh", response_model=TokensOut)
async def refresh(
    body: RefreshIn,
    request: HTTPRequest,
    session: AsyncSession = Depends(get_session),
) -> TokensOut:
    auth_rate_limiter.check(
        rate_key(request, "refresh", hashlib.sha256(body.refresh_token.encode()).hexdigest()),
        30,
        60,
    )
    access, refresh_token = await rotate_refresh(session, body.refresh_token)
    return TokensOut(access_token=access, refresh_token=refresh_token)


@app.get("/v1/auth/me", response_model=ParentOut)
async def me(parent: Parent = Depends(current_parent)) -> Parent:
    return parent


@app.post("/v1/auth/verification/request", status_code=202)
async def request_verification(
    request: HTTPRequest,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> None:
    auth_rate_limiter.check(rate_key(request, "verification", str(parent.id)), 5, 3600)
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
    body: TokenRequestIn, request: HTTPRequest, session: AsyncSession = Depends(get_session)
) -> None:
    auth_rate_limiter.check(rate_key(request, "password-reset", body.email.lower()), 5, 3600)
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
    await revoke_all_refresh(session, parent.id)
    await session.commit()


@app.post("/v1/auth/logout", status_code=204)
async def logout(
    body: RefreshIn,
    request: HTTPRequest,
    session: AsyncSession = Depends(get_session),
) -> None:
    auth_rate_limiter.check(
        rate_key(request, "logout", hashlib.sha256(body.refresh_token.encode()).hexdigest()),
        30,
        60,
    )
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
    await create_initial_bundle(session, child.id, parent.id, child.policy_document)
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
    policy_changed = False
    if body.name is not None:
        child.name = body.name
    if body.timezone is not None:
        child.timezone = validate_timezone(body.timezone)
        policy_changed = True
    if body.date_of_birth is not None:
        child.date_of_birth = body.date_of_birth
        child.age_band = age_band_for_dob(child.date_of_birth)
        policy_changed = True
    if policy_changed:
        raw_version = child.policy_document.get("policy_version", 0)
        current_version = raw_version if isinstance(raw_version, int) else 0
        child.policy_document = default_policy(
            family_id,
            child.id,
            child.age_band,
            child.timezone,
            policy_version=current_version + 1,
        )
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
    devices = list(
        (
            await session.scalars(select(Device).where(Device.child_profile_id == child.id))
        ).all()
    )
    now = datetime.now(UTC)
    for device in devices:
        device.revoked_at = now
        await session.execute(
            update(DeviceCredential)
            .where(DeviceCredential.device_id == device.id)
            .values(revoked_at=now)
        )
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
    request: HTTPRequest,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> None:
    await family_for_parent(session, parent, family_id)
    auth_rate_limiter.check(rate_key(request, "guardian-invite", body.email.lower()), 5, 60)
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
    request: HTTPRequest,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> None:
    auth_rate_limiter.check(rate_key(request, "guardian-accept", str(parent.id)), 10, 60)
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
        qr_payload=f"guardian://pair/{row.id}?code={code}&child_id={child_id}",
        expires_at=row.expires_at,
    )


@app.post("/v1/devices/pair", response_model=DeviceCredentialOut)
async def redeem_pairing(
    body: PairingRedeemIn,
    request: HTTPRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> DeviceCredentialOut:
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
    broadcaster.publish(
        family_id,
        {"type": "device-status", "device_id": str(device.id), "status": "REVOKED"},
        device.child_profile_id,
    )


@app.get("/v1/devices/me/policy")
async def fetch_policy(
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    bundle = await session.scalar(
        select(PolicyBundle).where(
            PolicyBundle.child_profile_id == device.child_profile_id,
            PolicyBundle.is_current.is_(True),
        )
    )
    if bundle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Policy not found")
    return {
        "bundle": bundle.new_value,
        "policy_version": bundle.policy_version,
        "version_mismatch": device.policy_version_applied != bundle.policy_version,
    }


@app.post("/v1/families/{family_id}/children/{child_id}/policy/mutations")
async def mutate_policy(
    family_id: UUID,
    child_id: UUID,
    body: PolicyMutationIn,
    parent: Parent = Depends(current_parent),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    await family_for_parent(session, parent, family_id)
    child = await session.scalar(
        select(ChildProfile).where(ChildProfile.id == child_id, ChildProfile.family_id == family_id)
    )
    if child is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Child not found")
    digest = payload_hash(body.model_dump(mode="json"))
    if idempotency_key is not None:
        replay = await replay_or_conflict(session, "policy_mutation", idempotency_key, digest)
        if replay is not None:
            return replay.response_body
    current = await session.scalar(
        select(PolicyBundle).where(
            PolicyBundle.child_profile_id == child_id, PolicyBundle.is_current.is_(True)
        )
    )
    if current is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Policy is unavailable")
    policy = deepcopy(current.new_value)
    policy["signature"] = ""
    operation = body.operation
    rule_id = f"{operation.lower()}-{UUID(int=secrets.randbits(128))}"
    if operation.startswith("APP_"):
        action = {
            "APP_ALLOW": "ALLOW",
            "APP_BLOCK": "BLOCK",
            "APP_UNLIMITED": "UNLIMITED",
            "APP_DAILY_MINUTES": "LIMIT",
            "APP_SCHEDULE": "SCHEDULE",
        }[operation]
        rule: dict[str, object] = {"rule_id": rule_id, "app_ref": body.target, "action": action}
        if action == "LIMIT":
            if not isinstance(body.value, int) or body.value < 0:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Daily minutes required")
            rule["daily_minutes"] = body.value
        if action == "SCHEDULE":
            if not isinstance(body.value, dict):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Schedule required")
            rule["schedule"] = body.value
        policy["app_rules"] = [*policy_records(policy, "app_rules"), rule]
    elif operation in {"DOMAIN_ALLOW", "DOMAIN_BLOCK"}:
        policy["domain_rules"] = [
            *policy_records(policy, "domain_rules"),
            {
                "rule_id": rule_id,
                "domain": body.target,
                "action": "ALLOW" if operation == "DOMAIN_ALLOW" else "BLOCK",
            },
        ]
    elif operation in {"CATEGORY_DAILY_MINUTES", "WEB_CATEGORY_ALLOW", "WEB_CATEGORY_BLOCK"}:
        if operation == "WEB_CATEGORY_ALLOW":
            action = "ALLOW"
        elif operation == "WEB_CATEGORY_BLOCK":
            action = "BLOCK"
        else:
            action = "LIMIT"
        if not isinstance(body.value, int) or body.value < 0:
            if operation == "CATEGORY_DAILY_MINUTES":
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Daily minutes required")
        policy["category_rules"] = [
            *policy_records(policy, "category_rules"),
            {
                "rule_id": rule_id,
                "category": body.target,
                "action": action,
                **({"daily_minutes": body.value} if action == "LIMIT" else {}),
            },
        ]
    elif operation == "UNKNOWN_DOMAIN_POLICY" or operation == "UNKNOWN_APP_POLICY":
        allowed = (
            {"BLOCK", "BLOCK_WHILE_CLASSIFYING", "ALLOW_WHILE_CLASSIFYING", "ALLOW_AND_NOTIFY"}
            if operation == "UNKNOWN_DOMAIN_POLICY"
            else {"BLOCK", "LIMIT_AND_NOTIFY", "ALLOW_AND_NOTIFY", "ALLOW"}
        )
        if body.value not in allowed:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid unknown policy")
        field = (
            "unknown_domain_policy"
            if operation == "UNKNOWN_DOMAIN_POLICY"
            else "unknown_app_policy"
        )
        base = policy_mapping(policy, "base_policy")
        base[field] = body.value
        policy["base_policy"] = base
    elif operation in {"ROUTINE_CREATE", "ROUTINE_UPDATE", "ROUTINE_DELETE"}:
        routines = policy_records(policy, "routines")
        if operation == "ROUTINE_DELETE":
            routines = [routine for routine in routines if routine.get("routine_id") != body.target]
        elif not isinstance(body.value, dict):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Routine value required")
        elif operation == "ROUTINE_CREATE":
            routines.append(body.value)
        else:
            replaced = False
            for index, routine in enumerate(routines):
                if routine.get("routine_id") == body.target:
                    routines[index] = body.value
                    replaced = True
            if not replaced:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Routine not found")
        policy["routines"] = routines
    elif operation == "COMMUNICATION_SENSITIVITY":
        if body.value not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid sensitivity")
        communication = policy_mapping(policy, "communication_safety")
        communication["severity_threshold"] = body.value
        policy["communication_safety"] = communication
    elif operation == "TEMPORARY_EXCEPTION":
        if body.expires_at is None or body.expires_at <= datetime.now(UTC):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Future expiry required")
        policy["temporary_overrides"] = [
            *policy_records(policy, "temporary_overrides"),
            {
                "rule_id": rule_id,
                "target_kind": "DOMAIN",
                "target_ref": body.target,
                "action": "ALLOW",
                "starts_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "expires_at": body.expires_at.isoformat().replace("+00:00", "Z"),
            },
        ]
    bundle = await create_next_bundle(
        session,
        child_id,
        parent.id,
        policy,
        {"operation": operation, "target": body.target, "value": body.value},
        expires_at=body.expires_at,
    )
    child.policy_document = bundle.new_value
    result = {
        "bundle": bundle.new_value,
        "policy_version": bundle.policy_version,
        "effective_at": bundle.effective_at.isoformat(),
        "author_parent_id": str(parent.id),
        "mutation_at": bundle.created_at.isoformat(),
        "expires_at": bundle.expires_at.isoformat() if bundle.expires_at else None,
        "previous_value": bundle.previous_value,
        "new_value": bundle.new_value,
        "superseded_policy_version": bundle.policy_version - 1,
    }
    if idempotency_key is not None:
        await save_result(
            session, "policy_mutation", idempotency_key, digest, status.HTTP_200_OK, result
        )
    await session.commit()
    broadcaster.publish(
        family_id,
        {"type": "policy-version-changed", "policy_version": bundle.policy_version},
        child_id,
    )
    return result


@app.post("/v1/devices/me/policy/ack", status_code=204)
async def acknowledge_policy(
    body: DeviceAckIn,
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> None:
    device.policy_version_applied = body.policy_version
    await session.commit()


@app.post(
    "/v1/devices/me/requests",
    response_model=RequestOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_request(
    body: RequestCreateIn,
    device: Device = Depends(current_device),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> RequestOut:
    payload = body.model_dump(mode="json")
    digest = payload_hash(payload)
    if idempotency_key is not None:
        replay = await replay_or_conflict(session, "request_create", idempotency_key, digest)
        if replay is not None:
            return RequestOut.model_validate(replay.response_body)
    request_row = RequestRow(
        child_profile_id=device.child_profile_id,
        device_id=device.id,
        request_type=body.request_type,
        subject=body.subject,
        reason=body.reason,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    session.add(request_row)
    await session.flush()
    result = RequestOut.model_validate(request_row)
    if idempotency_key is not None:
        await save_result(
            session,
            "request_create",
            idempotency_key,
            digest,
            status.HTTP_201_CREATED,
            result.model_dump(mode="json"),
        )
    await session.commit()
    family_id = await session.scalar(
        select(ChildProfile.family_id).where(ChildProfile.id == device.child_profile_id)
    )
    if family_id is not None:
        broadcaster.publish(
            family_id,
            {"type": "request-created", "request_id": str(request_row.id)},
            device.child_profile_id,
        )
    return result


@app.get("/v1/families/{family_id}/requests", response_model=list[RequestOut])
async def list_requests(
    family_id: UUID,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> list[RequestRow]:
    await family_for_parent(session, parent, family_id)
    rows = await session.scalars(
        select(RequestRow)
        .join(ChildProfile, ChildProfile.id == RequestRow.child_profile_id)
        .where(ChildProfile.family_id == family_id)
        .order_by(RequestRow.created_at.desc())
    )
    return list(rows.all())


async def decide_request(
    request_id: UUID,
    target: RequestState,
    body: RequestDecisionIn,
    parent: Parent,
    session: AsyncSession,
) -> RequestOut:
    row = await session.scalar(
        select(RequestRow)
        .join(ChildProfile, ChildProfile.id == RequestRow.child_profile_id)
        .join(Family, Family.id == ChildProfile.family_id)
        .join(FamilyGuardian, FamilyGuardian.family_id == Family.id)
        .where(RequestRow.id == request_id, FamilyGuardian.parent_id == parent.id)
        .with_for_update()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    if is_expired(row.expires_at):
        row.state = RequestState.EXPIRED.value
    transition(row.state, target)
    previous = row.state
    row.state = target.value
    row.decision_reason = body.reason
    row.decided_by_parent_id = parent.id
    row.decided_at = datetime.now(UTC)
    if target is RequestState.APPROVED:
        current = await session.scalar(
            select(PolicyBundle).where(
                PolicyBundle.child_profile_id == row.child_profile_id,
                PolicyBundle.is_current.is_(True),
            )
        )
        if current is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Policy is unavailable")
        policy = deepcopy(current.new_value)
        policy["signature"] = ""
        raw_overrides = policy.get("temporary_overrides", [])
        overrides = list(raw_overrides) if isinstance(raw_overrides, list) else []
        overrides.append(
            {
                "rule_id": f"request-{row.id}",
                "target_kind": "APP" if row.request_type == "UNBLOCK_APP" else "DOMAIN",
                "target_ref": row.subject or row.request_type,
                "action": "ALLOW",
                "starts_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "expires_at": (
                    datetime.now(UTC) + timedelta(hours=1)
                ).isoformat().replace("+00:00", "Z"),
            }
        )
        policy["temporary_overrides"] = overrides
        await create_next_bundle(
            session,
            row.child_profile_id,
            parent.id,
            policy,
            {"state": previous, "request_id": str(row.id)},
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    await session.commit()
    family_id = await session.scalar(
        select(ChildProfile.family_id).where(ChildProfile.id == row.child_profile_id)
    )
    if family_id is not None:
        broadcaster.publish(
            family_id,
            {"type": "request-decided", "request_id": str(row.id), "state": row.state},
            row.child_profile_id,
        )
    return RequestOut.model_validate(row)


@app.post("/v1/families/{family_id}/requests/{request_id}/approve", response_model=RequestOut)
async def approve_request(
    family_id: UUID,
    request_id: UUID,
    body: RequestDecisionIn,
    parent: Parent = Depends(current_parent),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> RequestOut:
    await family_for_parent(session, parent, family_id)
    digest = payload_hash(body.model_dump(mode="json"))
    if idempotency_key is not None:
        replay = await replay_or_conflict(session, "request_approval", idempotency_key, digest)
        if replay is not None:
            return RequestOut.model_validate(replay.response_body)
    result = await decide_request(request_id, RequestState.APPROVED, body, parent, session)
    if idempotency_key is not None:
        await save_result(
            session,
            "request_approval",
            idempotency_key,
            digest,
            status.HTTP_200_OK,
            result.model_dump(mode="json"),
        )
        await session.commit()
    return result


@app.post("/v1/families/{family_id}/requests/{request_id}/deny", response_model=RequestOut)
async def deny_request(
    family_id: UUID,
    request_id: UUID,
    body: RequestDecisionIn,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> RequestOut:
    await family_for_parent(session, parent, family_id)
    return await decide_request(request_id, RequestState.DENIED, body, parent, session)


@app.post("/v1/me/push-tokens", status_code=status.HTTP_204_NO_CONTENT)
async def register_push_token(
    body: PushTokenIn,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> None:
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    existing = await session.scalar(
        select(PushToken).where(
            PushToken.parent_id == parent.id,
            PushToken.token_hash == token_hash,
        )
    )
    if existing is None:
        session.add(PushToken(parent_id=parent.id, platform=body.platform, token_hash=token_hash))
    else:
        existing.active = True
        existing.platform = body.platform
    await session.commit()


@app.post("/v1/devices/me/push-tokens", status_code=status.HTTP_204_NO_CONTENT)
async def register_device_push_token(
    body: PushTokenIn,
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> None:
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    existing = await session.scalar(
        select(PushToken).where(
            PushToken.device_id == device.id,
            PushToken.token_hash == token_hash,
        )
    )
    if existing is None:
        session.add(
            PushToken(device_id=device.id, platform=body.platform, token_hash=token_hash)
        )
    else:
        existing.active = True
        existing.platform = body.platform
    await session.commit()


@app.get("/v1/families/{family_id}/health")
async def family_health(
    family_id: UUID,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    await family_for_parent(session, parent, family_id)
    settings = get_settings()
    now = datetime.now(UTC)
    children = list(
        (
            await session.scalars(select(ChildProfile).where(ChildProfile.family_id == family_id))
        ).all()
    )
    result: list[dict[str, object]] = []
    for child in children:
        devices = list(
            (
                await session.scalars(
                    select(Device).where(Device.child_profile_id == child.id)
                )
            ).all()
        )
        for device in devices:
            state = device.protection_state
            if device.revoked_at is not None:
                state = "UNKNOWN"
            elif device.last_seen_at is None or (
                now - device.last_seen_at
            ).total_seconds() > settings.health_stale_minutes * 60:
                state = "DEGRADED"
            result.append(
                {
                    "child_profile_id": child.id,
                    "device_id": device.id,
                    "state": state,
                    "last_seen_at": device.last_seen_at,
                    "policy_version_applied": device.policy_version_applied,
                }
            )
    return result


@app.websocket("/v1/ws/sync")
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


@app.post("/v1/devices/me/heartbeat", status_code=204)
async def heartbeat(
    body: DeviceHeartbeatIn,
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> None:
    device.protection_state = body.protection_state
    device.capabilities = {
        key: value.model_dump(mode="json", by_alias=True)
        for key, value in body.capabilities.items()
    }
    device.last_seen_at = datetime.now(UTC)
    session.add(
        ProtectionHealthEvent(
            device_id=device.id,
            occurred_at=device.last_seen_at,
            protection_state=body.protection_state,
            capabilities=device.capabilities,
        )
    )
    await session.commit()
    family_id = await session.scalar(
        select(ChildProfile.family_id).where(ChildProfile.id == device.child_profile_id)
    )
    if family_id is not None:
        broadcaster.publish(
            family_id,
            {
                "type": "protection-health-changed",
                "device_id": str(device.id),
                "protection_state": body.protection_state,
            },
            device.child_profile_id,
        )


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
    for event in body.events:
        event_type = event.event_type.upper()
        values = {
            "device_id": device.id,
            "event_type": event.event_type,
            "occurred_at": event.occurred_at,
            "app_ref": event.app_ref,
            "domain": event.domain,
        }
        if event_type in {"URL", "DOMAIN", "WEB"}:
            session.add(WebEvent(**values))
        elif event_type.startswith("SAFETY"):
            session.add(SafetyEvent(**values))
        else:
            session.add(
                UsageAggregate(
                    device_id=device.id,
                    event_type=event.event_type,
                    occurred_at=event.occurred_at,
                    app_ref=event.app_ref,
                    category=None,
                    duration_seconds=0,
                )
            )
    device.last_seen_at = datetime.now(UTC)
    if idempotency_key is not None:
        await save_result(session, "event_batch", idempotency_key, digest, 202, {})
    await session.commit()
