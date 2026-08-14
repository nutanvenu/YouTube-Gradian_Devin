from datetime import UTC, datetime

from fastapi import HTTPException, status

from .models import RequestState

TERMINAL_STATES = {
    RequestState.APPROVED.value,
    RequestState.DENIED.value,
    RequestState.EXPIRED.value,
    RequestState.CANCELLED.value,
}


def transition(current: str, target: RequestState) -> None:
    if current != RequestState.PENDING.value or target.value in TERMINAL_STATES - {
        RequestState.PENDING.value
    }:
        if current != RequestState.PENDING.value:
            raise HTTPException(status.HTTP_409_CONFLICT, "Request is already closed")
    else:
        raise HTTPException(status.HTTP_409_CONFLICT, "Invalid request transition")


def is_expired(expires_at: datetime | None) -> bool:
    return expires_at is not None and expires_at <= datetime.now(UTC)
