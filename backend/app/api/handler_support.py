# ruff: noqa: F401
import asyncio
import base64
import hashlib
import secrets
from binascii import Error as Base64Error
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import UUID

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import Depends, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi import Request as HTTPRequest
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.models import Parent
from ..auth.service import (
    DUMMY_PASSWORD_HASH,
    consume_one_time_token,
    hash_password,
    issue_one_time_token,
    issue_tokens,
    parent_from_access,
    revoke_all_refresh,
    revoke_refresh,
    rotate_refresh,
    verify_password,
)
from ..children.models import ChildAppInventory, ChildProfile
from ..core.config import get_settings
from ..core.db import get_session
from ..core.errors import (
    http_exception_handler,
    internal_error_handler,
    validation_error_handler,
)
from ..core.idempotency import payload_hash, replay_or_conflict, save_result
from ..core.notifier import LoggingNotifier
from ..core.rate_limit import InProcessRateLimiter
from ..devices.models import Device, DeviceCredential
from ..devices.service import current_device, verify_device_request_headers
from ..events.broadcaster import broadcaster
from ..events.models import (
    ProtectionHealthEvent,
    SafetyEvent,
    UsageAggregate,
    WebEvent,
)
from ..families.models import Family, FamilyGuardian, GuardianInvitation, GuardianRole
from ..pairing.models import PairingSession
from ..policies.models import PolicyBundle
from ..policies.service import (
    age_band_for_dob,
    create_initial_bundle,
    create_next_bundle,
    default_policy,
    validate_timezone,
)
from ..policies.signing import (
    configured_trusted_public_keys,
    signer,
    validate_configured_signing_key,
)
from ..push.models import PushAction, PushToken
from ..push.service import (
    LoggingPushSender,
    PushSender,
    issue_action_token,
    request_action_payload,
)
from ..requests.models import Request as RequestRow
from ..requests.models import RequestState
from ..requests.service import is_expired, transition
from .schemas import (
    ActivityEventOut,
    ActivityUsagePointOut,
    ChildCreate,
    ChildOut,
    ChildUpdate,
    DeviceAckIn,
    DeviceCredentialOut,
    DeviceHeartbeatIn,
    EventBatchIn,
    FamilyCreate,
    FamilyOut,
    GuardianAcceptIn,
    GuardianInviteIn,
    GuardianOut,
    LoginIn,
    ObservedAppBatchIn,
    ObservedAppIn,
    ObservedAppOut,
    PairingOut,
    PairingRedeemIn,
    ParentOut,
    PasswordResetConfirmIn,
    PolicyMutationIn,
    PushActionIn,
    PushTokenIn,
    RefreshIn,
    RequestCreateIn,
    RequestDecisionIn,
    RequestOut,
    SignupIn,
    TokenConfirmIn,
    TokenRequestIn,
    TokensOut,
)

__all__ = [
    'AsyncIterator',
    'AsyncSession',
    'ActivityEventOut',
    'ActivityUsagePointOut',
    'Base64Error',
    'ChildCreate',
    'ChildOut',
    'ChildAppInventory',
    'ChildProfile',
    'ChildUpdate',
    'DUMMY_PASSWORD_HASH',
    'Depends',
    'Device',
    'DeviceAckIn',
    'DeviceCredential',
    'DeviceCredentialOut',
    'DeviceHeartbeatIn',
    'Ed25519PublicKey',
    'EventBatchIn',
    'ObservedAppBatchIn',
    'ObservedAppIn',
    'ObservedAppOut',
    'Family',
    'FamilyCreate',
    'FamilyGuardian',
    'FamilyOut',
    'GuardianAcceptIn',
    'GuardianInvitation',
    'GuardianInviteIn',
    'GuardianOut',
    'GuardianRole',
    'HTTPException',
    'HTTPRequest',
    'Header',
    'InProcessRateLimiter',
    'LoggingNotifier',
    'LoginIn',
    'Mapping',
    'OAuth2PasswordBearer',
    'PairingOut',
    'PairingRedeemIn',
    'PairingSession',
    'Parent',
    'ParentOut',
    'PasswordResetConfirmIn',
    'PolicyBundle',
    'PolicyMutationIn',
    'ProtectionHealthEvent',
    'PushToken',
    'PushAction',
    'PushTokenIn',
    'PushActionIn',
    'RefreshIn',
    'RequestCreateIn',
    'RequestDecisionIn',
    'RequestOut',
    'RequestRow',
    'RequestState',
    'RequestValidationError',
    'SafetyEvent',
    'SignupIn',
    'TokenConfirmIn',
    'TokenRequestIn',
    'TokensOut',
    'UTC',
    'UUID',
    'UsageAggregate',
    'WebEvent',
    'WebSocket',
    'WebSocketDisconnect',
    'age_band_for_dob',
    'asynccontextmanager',
    'asyncio',
    'auth_rate_limiter',
    'base64',
    'broadcaster',
    'LoggingPushSender',
    'PushSender',
    'push_sender',
    'issue_action_token',
    'request_action_payload',
    'configured_trusted_public_keys',
    'consume_one_time_token',
    'create_initial_bundle',
    'create_next_bundle',
    'current_device',
    'current_parent',
    'datetime',
    'deepcopy',
    'default_policy',
    'family_for_parent',
    'get_session',
    'get_settings',
    'hash_password',
    'hashlib',
    'http_exception_handler',
    'internal_error_handler',
    'is_expired',
    'issue_one_time_token',
    'issue_tokens',
    'notifier',
    'oauth2',
    'parent_from_access',
    'payload_hash',
    'policy_mapping',
    'policy_records',
    'rate_key',
    'replay_or_conflict',
    'revoke_all_refresh',
    'revoke_refresh',
    'rotate_refresh',
    'save_result',
    'secrets',
    'select',
    'signer',
    'status',
    'timedelta',
    'transition',
    'update',
    'validate_configured_signing_key',
    'validate_timezone',
    'validation_error_handler',
    'verify_device_request_headers',
    'verify_password',
]

oauth2 = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")
auth_rate_limiter = InProcessRateLimiter()
notifier = LoggingNotifier()
push_sender: PushSender = LoggingPushSender()

def policy_records(policy: dict[str, object], key: str) -> list[dict[str, object]]:
    value = policy.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]

def policy_mapping(policy: dict[str, object], key: str) -> dict[str, object]:
    value = policy.get(key)
    if not isinstance(value, Mapping):
        raise HTTPException(status.HTTP_409_CONFLICT, "Policy is malformed")
    return dict(value)

def rate_key(request: HTTPRequest, operation: str, principal: str) -> str:
    client_ip = request.client.host if request.client is not None else "unknown"
    return f"{operation}:{client_ip}:{principal}"

async def current_parent(
    token: str = Depends(oauth2), session: AsyncSession = Depends(get_session)
) -> Parent:
    return await parent_from_access(session, token)

async def family_for_parent(session: AsyncSession, parent: Parent, family_id: UUID) -> Family:
    family = await session.scalar(
        select(Family)
        .join(FamilyGuardian)
        .where(Family.id == family_id, FamilyGuardian.parent_id == parent.id)
    )
    if family is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Family not found")
    return family
