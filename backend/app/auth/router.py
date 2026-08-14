# ruff: noqa: E501
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import delete

from ..api.handler_support import (
    DUMMY_PASSWORD_HASH,
    UTC,
    AsyncSession,
    Depends,
    HTTPException,
    HTTPRequest,
    LoginIn,
    Parent,
    PasswordResetConfirmIn,
    RefreshIn,
    SignupIn,
    TokenConfirmIn,
    TokenRequestIn,
    TokensOut,
    auth_rate_limiter,
    consume_one_time_token,
    current_parent,
    datetime,
    get_session,
    hash_password,
    hashlib,
    issue_one_time_token,
    issue_tokens,
    notifier,
    rate_key,
    revoke_all_refresh,
    revoke_refresh,
    rotate_refresh,
    select,
    status,
    timedelta,
    verify_password,
)
from ..children.models import ChildAppInventory, ChildProfile
from ..devices.models import Device, DeviceCredential
from ..events.models import (
    ProtectionHealthEvent,
    SafetyEvent,
    SafetyNotification,
    UsageAggregate,
    WebEvent,
)
from ..families.models import Family, FamilyGuardian, GuardianInvitation
from ..pairing.models import PairingSession
from ..policies.models import PolicyBundle, PolicyDocument
from ..push.models import PushAction, PushToken
from ..requests.models import Request

router = APIRouter()


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

async def me(parent: Parent = Depends(current_parent)) -> Parent:
    return parent

async def request_verification(
    request: HTTPRequest,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> None:
    auth_rate_limiter.check(rate_key(request, "verification", str(parent.id)), 5, 3600)
    token = await issue_one_time_token(session, parent, "EMAIL_VERIFY", timedelta(hours=24))
    await notifier.send_email(parent.email, "Verify your Guardian email", token)
    await session.commit()

async def confirm_verification(
    body: TokenConfirmIn, session: AsyncSession = Depends(get_session)
) -> None:
    parent = await consume_one_time_token(session, body.token, "EMAIL_VERIFY")
    parent.email_verified_at = datetime.now(UTC)
    await session.commit()

async def request_password_reset(
    body: TokenRequestIn, request: HTTPRequest, session: AsyncSession = Depends(get_session)
) -> None:
    auth_rate_limiter.check(rate_key(request, "password-reset", body.email.lower()), 5, 3600)
    parent = await session.scalar(select(Parent).where(Parent.email == body.email.lower()))
    if parent is not None:
        token = await issue_one_time_token(session, parent, "PASSWORD_RESET", timedelta(hours=1))
        await notifier.send_email(parent.email, "Reset your Guardian password", token)
        await session.commit()

async def confirm_password_reset(
    body: PasswordResetConfirmIn, session: AsyncSession = Depends(get_session)
) -> None:
    parent = await consume_one_time_token(session, body.token, "PASSWORD_RESET")
    parent.password_hash = hash_password(body.password)
    await revoke_all_refresh(session, parent.id)
    await session.commit()

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

async def delete_account(
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> None:
    family_ids = list(
        (
            await session.scalars(
                select(FamilyGuardian.family_id).where(
                    FamilyGuardian.parent_id == parent.id
                )
            )
        ).all()
    )
    child_ids = list(
        (
            await session.scalars(
                select(ChildProfile.id).where(ChildProfile.family_id.in_(family_ids))
            )
        ).all()
    )
    device_ids = list(
        (
            await session.scalars(
                select(Device.id).where(Device.child_profile_id.in_(child_ids))
            )
        ).all()
    )

    if child_ids:
        await session.execute(
            delete(SafetyNotification).where(
                SafetyNotification.child_profile_id.in_(child_ids)
            )
        )
    if device_ids:
        await session.execute(delete(PushToken).where(PushToken.device_id.in_(device_ids)))
        await session.execute(
            delete(DeviceCredential).where(DeviceCredential.device_id.in_(device_ids))
        )
        await session.execute(delete(SafetyEvent).where(SafetyEvent.device_id.in_(device_ids)))
        await session.execute(delete(WebEvent).where(WebEvent.device_id.in_(device_ids)))
        await session.execute(
            delete(UsageAggregate).where(UsageAggregate.device_id.in_(device_ids))
        )
        await session.execute(
            delete(ProtectionHealthEvent).where(
                ProtectionHealthEvent.device_id.in_(device_ids)
            )
        )
    if child_ids:
        await session.execute(delete(Request).where(Request.child_profile_id.in_(child_ids)))
        await session.execute(
            delete(PolicyBundle).where(PolicyBundle.child_profile_id.in_(child_ids))
        )
        await session.execute(
            delete(PolicyDocument).where(PolicyDocument.child_profile_id.in_(child_ids))
        )
        await session.execute(
            delete(ChildAppInventory).where(
                ChildAppInventory.child_profile_id.in_(child_ids)
            )
        )
        await session.execute(
            delete(PairingSession).where(PairingSession.child_profile_id.in_(child_ids))
        )
    if family_ids:
        await session.execute(
            delete(GuardianInvitation).where(
                GuardianInvitation.family_id.in_(family_ids)
            )
        )
        await session.execute(
            delete(FamilyGuardian).where(FamilyGuardian.family_id.in_(family_ids))
        )
        await session.execute(delete(ChildProfile).where(ChildProfile.id.in_(child_ids)))
        await session.execute(delete(Family).where(Family.id.in_(family_ids)))

    await session.execute(delete(PushAction).where(PushAction.parent_id == parent.id))
    await session.execute(delete(PushToken).where(PushToken.parent_id == parent.id))
    await session.delete(parent)
    await session.commit()

async def account_deletion_page() -> HTMLResponse:
    return HTMLResponse(
        """<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><title>Delete your Guardian account</title></head>
  <body>
    <main>
      <h1>Delete your Guardian account</h1>
      <p>Sign in to Guardian, open Account, choose Delete account, and confirm the irreversible action.</p>
      <p>Account deletion removes your family, child profiles, devices, policies, events, reports, requests, and notification records.</p>
      <p>To request deletion from a browser, use the authenticated account deletion endpoint:
        <code>DELETE /v1/auth/account</code>.</p>
    </main>
  </body>
</html>"""
    )

router.add_api_route("/v1/auth/signup", signup, methods=["POST"], status_code=201)
router.add_api_route("/v1/auth/login", login, methods=["POST"])
router.add_api_route("/v1/auth/refresh", refresh, methods=["POST"])
router.add_api_route("/v1/auth/me", me, methods=["GET"], response_model=None)
router.add_api_route("/v1/auth/verification/request", request_verification, methods=["POST"], status_code=202)
router.add_api_route("/v1/auth/verification/confirm", confirm_verification, methods=["POST"], status_code=204)
router.add_api_route("/v1/auth/password-reset/request", request_password_reset, methods=["POST"], status_code=202)
router.add_api_route("/v1/auth/password-reset/confirm", confirm_password_reset, methods=["POST"], status_code=204)
router.add_api_route("/v1/auth/logout", logout, methods=["POST"], status_code=204)
router.add_api_route("/v1/auth/account", delete_account, methods=["DELETE"], status_code=204)
router.add_api_route("/account-deletion", account_deletion_page, methods=["GET"])
