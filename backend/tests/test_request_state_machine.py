import pytest
from fastapi import HTTPException

from app.requests.models import RequestState
from app.requests.service import transition


@pytest.mark.parametrize(
    ("target",),
    [
        (RequestState.APPROVED,),
        (RequestState.DENIED,),
        (RequestState.EXPIRED,),
        (RequestState.CANCELLED,),
    ],
)
def test_pending_allows_each_terminal_transition(target: RequestState) -> None:
    transition(RequestState.PENDING.value, target)


@pytest.mark.parametrize("current", list(RequestState))
@pytest.mark.parametrize("target", list(RequestState))
def test_terminal_and_invalid_transitions_are_rejected(
    current: RequestState, target: RequestState
) -> None:
    if current is RequestState.PENDING and target in {
        RequestState.APPROVED,
        RequestState.DENIED,
        RequestState.EXPIRED,
        RequestState.CANCELLED,
    }:
        return
    with pytest.raises(HTTPException):
        transition(current.value, target)


@pytest.mark.asyncio
async def test_unmatched_more_time_subject_cannot_fall_back_to_a_device_grant(
    client, paired_device, database_session
) -> None:
    import json

    from sqlalchemy import select

    from app.policies.models import PolicyBundle
    from app.requests.models import Request

    body = json.dumps(
        {"request_type": "MORE_TIME", "subject": "a label with no exact target"},
        separators=(",", ":"),
    ).encode()
    created = await client.post(
        "/v1/devices/me/requests",
        content=body,
        headers=paired_device.signed_headers("/v1/devices/me/requests", body),
    )
    assert created.status_code == 201, created.text
    approved = await client.post(
        f"/v1/families/{paired_device.parent.family_id}/requests/{created.json()['id']}/approve",
        headers={"Authorization": f"Bearer {paired_device.parent.token}"},
        json={"reason": "Only an exact target can be approved"},
    )
    assert approved.status_code == 422
    request = await database_session.get(Request, created.json()["id"])
    assert request is not None
    assert request.state == RequestState.PENDING
    current = await database_session.scalar(
        select(PolicyBundle).where(
            PolicyBundle.child_profile_id == paired_device.parent.child_id,
            PolicyBundle.is_current.is_(True),
        )
    )
    assert current is not None
    assert current.policy_version == 1
