import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from .models import Parent, RefreshToken

password_hasher = PasswordHasher()


def hash_password(value: str) -> str:
    return password_hasher.hash(value)


def verify_password(value: str, encoded: str) -> bool:
    try:
        return password_hasher.verify(encoded, value)
    except Exception:
        return False


def _hash_token(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _jwt(parent_id: UUID, token_type: str, expires: timedelta) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": str(parent_id), "type": token_type, "iat": now, "exp": now + expires},
        get_settings().jwt_secret,
        algorithm="HS256",
    )


async def issue_tokens(session: AsyncSession, parent: Parent) -> tuple[str, str]:
    refresh_raw = secrets.token_urlsafe(48)
    now = datetime.now(UTC)
    row = RefreshToken(
        parent_id=parent.id,
        token_hash=_hash_token(refresh_raw),
        expires_at=now + timedelta(days=get_settings().refresh_days),
    )
    session.add(row)
    await session.flush()
    return _jwt(parent.id, "access", timedelta(minutes=get_settings().access_minutes)), refresh_raw


async def parent_from_access(session: AsyncSession, token: str) -> Parent:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise ValueError
        parent_id = UUID(str(payload["sub"]))
    except (KeyError, ValueError, jwt.PyJWTError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid access token") from exc
    parent = await session.get(Parent, parent_id)
    if parent is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid access token")
    return parent


async def rotate_refresh(session: AsyncSession, raw: str) -> tuple[str, str]:
    row = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw))
    )
    if row is None or row.revoked_at is not None or row.expires_at <= datetime.now(UTC):
        if row is not None and row.revoked_at is not None:
            await session.execute(
                update(RefreshToken)
                .where(RefreshToken.parent_id == row.parent_id)
                .values(revoked_at=datetime.now(UTC))
            )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token is invalid")
    parent = await session.get(Parent, row.parent_id)
    if parent is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token is invalid")
    row.revoked_at = datetime.now(UTC)
    access, refresh = await issue_tokens(session, parent)
    await session.commit()
    return access, refresh


async def revoke_refresh(session: AsyncSession, raw: str) -> None:
    row = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw))
    )
    if row is not None:
        row.revoked_at = datetime.now(UTC)
        await session.commit()
