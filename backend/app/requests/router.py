# ruff: noqa: E501
from fastapi import APIRouter

from ..api.handler_support import (
    UTC,
    UUID,
    AsyncSession,
    ChildProfile,
    Depends,
    Family,
    FamilyGuardian,
    Header,
    HTTPException,
    Parent,
    PolicyBundle,
    RequestDecisionIn,
    RequestOut,
    RequestRow,
    RequestState,
    broadcaster,
    create_next_bundle,
    current_parent,
    datetime,
    deepcopy,
    family_for_parent,
    get_session,
    is_expired,
    payload_hash,
    replay_or_conflict,
    save_result,
    select,
    status,
    timedelta,
    transition,
)
from ..policies.temporary import build_more_time_override

router = APIRouter()


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
        expires_at = datetime.now(UTC) + timedelta(hours=1)
        if row.request_type == "MORE_TIME":
            starts_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            overrides.append(
                build_more_time_override(
                    policy,
                    row.subject,
                    15,
                    f"request-{row.id}",
                    starts_at,
                    expires_at.isoformat().replace("+00:00", "Z"),
                )
            )
        else:
            overrides.append(
                {
                    "rule_id": f"request-{row.id}",
                    "target_kind": "APP" if row.request_type == "UNBLOCK_APP" else "DOMAIN",
                    "target_ref": row.subject or row.request_type,
                    "action": "ALLOW",
                    "starts_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
                }
            )
        policy["temporary_overrides"] = overrides
        await create_next_bundle(
            session,
            row.child_profile_id,
            parent.id,
            policy,
            {"state": previous, "request_id": str(row.id)},
            expires_at=expires_at,
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

async def deny_request(
    family_id: UUID,
    request_id: UUID,
    body: RequestDecisionIn,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> RequestOut:
    await family_for_parent(session, parent, family_id)
    return await decide_request(request_id, RequestState.DENIED, body, parent, session)

router.add_api_route("/v1/families/{family_id}/requests", list_requests, methods=["GET"], response_model=None)
router.add_api_route("/v1/families/{family_id}/requests/{request_id}/approve", approve_request, methods=["POST"], response_model=None)
router.add_api_route("/v1/families/{family_id}/requests/{request_id}/deny", deny_request, methods=["POST"], response_model=None)
