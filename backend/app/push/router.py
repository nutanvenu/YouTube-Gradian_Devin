# ruff: noqa: E501
from fastapi import APIRouter

from ..api.handler_support import (
    AsyncSession,
    Depends,
    Parent,
    PushToken,
    PushTokenIn,
    current_parent,
    get_session,
    hashlib,
    select,
)

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

router.add_api_route("/v1/me/push-tokens", register_push_token, methods=["POST"], status_code=204, response_model=None)
