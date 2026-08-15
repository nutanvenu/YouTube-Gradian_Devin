# ruff: noqa: E501
from fastapi import APIRouter

from ..api.handler_support import (
    UTC,
    AsyncSession,
    ChildProfile,
    Depends,
    FamilyGuardian,
    HTTPException,
    Parent,
    PushAction,
    PushActionIn,
    PushToken,
    PushTokenIn,
    RequestDecisionIn,
    RequestOut,
    RequestRow,
    RequestState,
    current_parent,
    datetime,
    get_session,
    hashlib,
    is_expired,
    select,
    status,
)
from ..requests.router import decide_request

router = APIRouter()


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


async def apply_push_action(
    action_token: str,
    expected_action: RequestState,
    body: PushActionIn,
    session: AsyncSession,
) -> RequestOut:
    row = await session.scalar(
        select(PushAction).where(
            PushAction.token_hash == hashlib.sha256(action_token.encode()).hexdigest()
        )
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Push action is invalid")
    action_name = "APPROVE" if expected_action is RequestState.APPROVED else "DENY"
    if row.action != action_name:
        raise HTTPException(status.HTTP_409_CONFLICT, "Push action does not match")
    request_row = await session.scalar(
        select(RequestRow).where(RequestRow.id == row.request_id).with_for_update()
    )
    if request_row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    guardian = await session.scalar(
        select(FamilyGuardian)
        .join(ChildProfile, ChildProfile.family_id == FamilyGuardian.family_id)
        .where(
            FamilyGuardian.parent_id == row.parent_id,
            ChildProfile.id == request_row.child_profile_id,
        )
    )
    if guardian is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Parent is no longer authorized")
    if is_expired(row.expires_at):
        raise HTTPException(status.HTTP_410_GONE, "Push action has expired")
    target = (
        RequestState.APPROVED
        if expected_action is RequestState.APPROVED
        else RequestState.DENIED
    )
    if request_row.state == target.value:
        return RequestOut.model_validate(request_row)
    if row.used_at is not None or request_row.state != RequestState.PENDING.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Request is already closed")
    parent = await session.get(Parent, row.parent_id)
    if parent is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Parent is no longer authorized")
    result = await decide_request(
        request_row.id,
        target,
        RequestDecisionIn(reason=body.reason or f"{target.value.title()} from notification"),
        parent,
        session,
    )
    row.used_at = datetime.now(UTC)
    await session.commit()
    return result


async def approve_push_action(
    action_token: str,
    body: PushActionIn,
    session: AsyncSession = Depends(get_session),
) -> RequestOut:
    return await apply_push_action(action_token, RequestState.APPROVED, body, session)


async def deny_push_action(
    action_token: str,
    body: PushActionIn,
    session: AsyncSession = Depends(get_session),
) -> RequestOut:
    return await apply_push_action(action_token, RequestState.DENIED, body, session)


router.add_api_route(
    "/v1/me/push-tokens",
    register_push_token,
    methods=["POST"],
    status_code=204,
    response_model=None,
)
router.add_api_route(
    "/v1/push/actions/{action_token}/approve",
    approve_push_action,
    methods=["POST"],
    response_model=RequestOut,
)
router.add_api_route(
    "/v1/push/actions/{action_token}/deny",
    deny_push_action,
    methods=["POST"],
    response_model=RequestOut,
)
