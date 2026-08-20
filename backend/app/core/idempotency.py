import hashlib
import json
from collections.abc import Mapping

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import IdempotencyRecord


def payload_hash(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


async def acquire_idempotency_lock(
    session: AsyncSession, operation: str, key: str
) -> None:
    """Serialize a key's lookup and insert for the current transaction.

    The unique constraint remains the durable backstop.  This transaction-scoped
    advisory lock makes the normal replay path deterministic rather than
    relying on a unique-constraint race after a policy/request has changed.
    Hash collisions only serialize unrelated keys; they cannot replay data.
    """
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
        {"lock_key": f"{operation}:{key}"},
    )


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
