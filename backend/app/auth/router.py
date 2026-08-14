# ruff: noqa: E501
from fastapi import APIRouter

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

router.add_api_route("/v1/auth/signup", signup, methods=["POST"], status_code=201)
router.add_api_route("/v1/auth/login", login, methods=["POST"])
router.add_api_route("/v1/auth/refresh", refresh, methods=["POST"])
router.add_api_route("/v1/auth/me", me, methods=["GET"], response_model=None)
router.add_api_route("/v1/auth/verification/request", request_verification, methods=["POST"], status_code=202)
router.add_api_route("/v1/auth/verification/confirm", confirm_verification, methods=["POST"], status_code=204)
router.add_api_route("/v1/auth/password-reset/request", request_password_reset, methods=["POST"], status_code=202)
router.add_api_route("/v1/auth/password-reset/confirm", confirm_password_reset, methods=["POST"], status_code=204)
router.add_api_route("/v1/auth/logout", logout, methods=["POST"], status_code=204)
