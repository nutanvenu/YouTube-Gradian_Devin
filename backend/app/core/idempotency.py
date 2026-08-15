import hashlib
import json
from collections.abc import Mapping

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import IdempotencyRecord


def payload_hash(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


async def replay_or_conflict(
    session: AsyncSession, operation: str, key: str, digest: str
) -> IdempotencyRecord | None:
    record = await session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.operation == operation,
            IdempotencyRecord.idempotency_key == key,
        )
    )
    if record is not None and record.payload_hash != digest:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Idempotency key was reused with a different payload"
        )
    return record


async def save_result(
    session: AsyncSession,
    operation: str,
    key: str,
    digest: str,
    status_code: int,
    response_body: dict[str, object],
) -> None:
    session.add(
        IdempotencyRecord(
            operation=operation,
            idempotency_key=key,
            payload_hash=digest,
            status_code=status_code,
            response_body=response_body,
        )
    )
