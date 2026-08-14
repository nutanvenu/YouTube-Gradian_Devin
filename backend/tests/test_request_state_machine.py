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
