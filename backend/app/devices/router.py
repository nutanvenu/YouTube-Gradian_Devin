# ruff: noqa: E501
from datetime import date
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from sqlalchemy import and_, func, or_
from sqlalchemy.dialects.postgresql import insert

from ..api.handler_support import (
    UTC,
    UUID,
    AsyncSession,
    ChildAppInventory,
    ChildProfile,
    Depends,
    Device,
    DeviceAckIn,
    DeviceHeartbeatIn,
    EventBatchIn,
    FamilyGuardian,
    Header,
    HTTPException,
    HTTPRequest,
    ObservedAppBatchIn,
    PolicyBundle,
    ProtectionHealthEvent,
    PushAction,
    PushToken,
    PushTokenIn,
    RequestCreateIn,
    RequestOut,
    RequestRow,
    SafetyEvent,
    UsageAggregate,
    WebEvent,
    broadcaster,
    current_device,
    datetime,
    get_session,
    hashlib,
    issue_action_token,
    payload_hash,
    push_sender,
    replay_or_conflict,
    request_action_payload,
    route_safety_notifications,
    save_result,
    select,
    status,
    timedelta,
    verify_device_request_headers,
)

router = APIRouter()


def usage_snapshot_identity(
    *,
    occurred_at: datetime,
    timezone: str,
    app_ref: str | None,
    category: str | None,
) -> tuple[date, str]:
    """Return the source-local daily key for a cumulative usage snapshot."""
    try:
        snapshot_day = occurred_at.astimezone(ZoneInfo(timezone)).date()
    except Exception:
        snapshot_day = occurred_at.astimezone(UTC).date()
    if app_ref:
        return snapshot_day, f"APP:{app_ref}"
    if category:
        return snapshot_day, f"CATEGORY:{category}"
    return snapshot_day, "DEVICE"


async def upsert_usage_snapshot(
    session: AsyncSession,
    *,
    device_id: UUID,
    event_type: str,
    occurred_at: datetime,
    timezone: str,
    app_ref: str | None,
    category: str | None,
    duration_seconds: int,
) -> None:
    """Persist exactly one latest cumulative usage value per device/target/day."""
    snapshot_day, snapshot_key = usage_snapshot_identity(
        occurred_at=occurred_at,
        timezone=timezone,
        app_ref=app_ref,
        category=category,
    )
    statement = insert(UsageAggregate).values(
        device_id=device_id,
        event_type=event_type,
        occurred_at=occurred_at,
        app_ref=app_ref,
        category=category,
        timezone=timezone,
        duration_seconds=duration_seconds,
        snapshot_day=snapshot_day,
        snapshot_key=snapshot_key,
    )
    excluded = statement.excluded
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[
                UsageAggregate.device_id,
                UsageAggregate.snapshot_day,
                UsageAggregate.snapshot_key,
            ],
            index_where=and_(
                UsageAggregate.snapshot_day.is_not(None),
                UsageAggregate.snapshot_key.is_not(None),
            ),
            set_={
                "event_type": excluded.event_type,
                "occurred_at": excluded.occurred_at,
                "app_ref": excluded.app_ref,
                "category": excluded.category,
                "timezone": excluded.timezone,
                # UsageStats sends a cumulative daily counter. A delayed,
                # lower sample (including a relaunch retry) must not reduce a
                # parent's already observed total.
                "duration_seconds": func.greatest(
                    UsageAggregate.duration_seconds, excluded.duration_seconds
                ),
            },
            where=or_(
                excluded.occurred_at > UsageAggregate.occurred_at,
                excluded.occurred_at == UsageAggregate.occurred_at,
            ),
        )
    )


async def fetch_policy(
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    bundle = await session.scalar(
        select(PolicyBundle).where(
            PolicyBundle.child_profile_id == device.child_profile_id,
            PolicyBundle.is_current.is_(True),
        )
    )
    if bundle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Policy not found")
    return {
        "bundle": bundle.new_value,
        "policy_version": bundle.policy_version,
        "version_mismatch": device.policy_version_applied != bundle.policy_version,
    }

async def acknowledge_policy(
    body: DeviceAckIn,
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> None:
    device.policy_version_applied = body.policy_version
    await session.commit()

async def heartbeat(
    body: DeviceHeartbeatIn,
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> None:
    device.protection_state = body.protection_state
    device.capabilities = {
        key: value.model_dump(mode="json", by_alias=True)
        for key, value in body.capabilities.items()
    }
    device.last_seen_at = datetime.now(UTC)
    session.add(
        ProtectionHealthEvent(
            device_id=device.id,
            occurred_at=device.last_seen_at,
            protection_state=body.protection_state,
            capabilities=device.capabilities,
        )
    )
    family_id = await session.scalar(
        select(ChildProfile.family_id).where(ChildProfile.id == device.child_profile_id)
    )
    await session.commit()
    if family_id is not None:
        broadcaster.publish(
            family_id,
            {
                "type": "protection-health-changed",
                "device_id": str(device.id),
                "protection_state": body.protection_state,
            },
            device.child_profile_id,
        )

async def ingest_events(
    body: EventBatchIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> None:
    digest = payload_hash(body.model_dump(mode="json"))
    if idempotency_key is not None:
        replay = await replay_or_conflict(session, "event_batch", idempotency_key, digest)
        if replay is not None:
            return
    device_timezone = await session.scalar(
        select(ChildProfile.timezone).where(ChildProfile.id == device.child_profile_id)
    )
    safety_rows: list[SafetyEvent] = []
    for event in body.events:
        event_type = event.event_type.upper()
        values = {
            "device_id": device.id,
            "event_type": event.event_type,
            "occurred_at": event.occurred_at,
            "app_ref": event.app_ref,
            "domain": event.domain,
            "category": event.category,
        }
        if event_type in {"URL", "DOMAIN", "WEB"} or event_type.startswith("WEB_"):
            session.add(WebEvent(**values))
        elif event_type.startswith("SAFETY"):
            row = SafetyEvent(
                **values,
                severity=event.severity,
                confidence=event.confidence,
                reason_code=event.reason_code,
            )
            session.add(row)
            safety_rows.append(row)
        else:
            await upsert_usage_snapshot(
                session,
                device_id=device.id,
                event_type=event.event_type,
                occurred_at=event.occurred_at,
                app_ref=event.app_ref,
                category=event.category,
                timezone=event.timezone or device_timezone or "UTC",
                duration_seconds=event.duration_seconds,
            )
    device.last_seen_at = datetime.now(UTC)
    await session.flush()
    deliveries = await route_safety_notifications(session, safety_rows, push_sender)
    if idempotency_key is not None:
        await save_result(session, "event_batch", idempotency_key, digest, 202, {})
    await session.commit()
    for parent_id, payload in deliveries:
        await push_sender.send(parent_id, payload)


async def ingest_inventory(
    body: ObservedAppBatchIn,
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> None:
    for app in body.apps:
        await session.execute(
            insert(ChildAppInventory)
            .values(
                child_profile_id=device.child_profile_id,
                platform_app_id=app.platform_app_id,
                display_name=app.display_name,
                category=app.category,
                observed_at=app.observed_at,
            )
            .on_conflict_do_update(
                index_elements=[
                    ChildAppInventory.child_profile_id,
                    ChildAppInventory.platform_app_id,
                ],
                set_={
                    "display_name": app.display_name,
                    "category": app.category,
                    "observed_at": app.observed_at,
                },
            )
        )
    device.last_seen_at = datetime.now(UTC)
    await session.commit()

async def create_request(
    body: RequestCreateIn,
    request: HTTPRequest,
    device: Device = Depends(current_device),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> RequestOut:
    await verify_device_request_headers(request, device, session)
    payload = body.model_dump(mode="json")
    digest = payload_hash(payload)
    if idempotency_key is not None:
        replay = await replay_or_conflict(session, "request_create", idempotency_key, digest)
        if replay is not None:
            return RequestOut.model_validate(replay.response_body)
    request_row = RequestRow(
        child_profile_id=device.child_profile_id,
        device_id=device.id,
        request_type=body.request_type,
        subject=body.subject,
        reason=body.reason,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    session.add(request_row)
    await session.flush()
    result = RequestOut.model_validate(request_row)
    if idempotency_key is not None:
        await save_result(
            session,
            "request_create",
            idempotency_key,
            digest,
            status.HTTP_201_CREATED,
            result.model_dump(mode="json"),
        )
    family_id = await session.scalar(
        select(ChildProfile.family_id).where(ChildProfile.id == device.child_profile_id)
    )
    deliveries: list[tuple[UUID, dict[str, object]]] = []
    if family_id is not None:
        parent_ids = await session.scalars(
            select(FamilyGuardian.parent_id)
            .join(PushToken, PushToken.parent_id == FamilyGuardian.parent_id)
            .where(
                FamilyGuardian.family_id == family_id,
                PushToken.active.is_(True),
            )
        )
        for parent_id in set(parent_ids.all()):
            approve_token, approve_hash = issue_action_token()
            deny_token, deny_hash = issue_action_token()
            expires_at = request_row.expires_at or datetime.now(UTC) + timedelta(hours=1)
            session.add_all(
                [
                    PushAction(
                        request_id=request_row.id,
                        parent_id=parent_id,
                        action="APPROVE",
                        token_hash=approve_hash,
                        expires_at=expires_at,
                    ),
                    PushAction(
                        request_id=request_row.id,
                        parent_id=parent_id,
                        action="DENY",
                        token_hash=deny_hash,
                        expires_at=expires_at,
                    ),
                ]
            )
            deliveries.append(
                (
                    parent_id,
                    request_action_payload(
                        request_id=request_row.id,
                        request_type=request_row.request_type,
                        subject=request_row.subject,
                        approve_token=approve_token,
                        deny_token=deny_token,
                    ),
                )
            )
    await session.commit()
    if family_id is not None:
        broadcaster.publish(
            family_id,
            {"type": "request-created", "request_id": str(request_row.id)},
            device.child_profile_id,
        )
    for parent_id, payload in deliveries:
        await push_sender.send(parent_id, payload)
    return result

async def register_device_push_token(
    body: PushTokenIn,
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> None:
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    existing = await session.scalar(
        select(PushToken).where(
            PushToken.device_id == device.id,
            PushToken.token_hash == token_hash,
        )
    )
    if existing is None:
        session.add(
            PushToken(device_id=device.id, platform=body.platform, token_hash=token_hash)
        )
    else:
        existing.active = True
        existing.platform = body.platform
    await session.commit()

router.add_api_route("/v1/devices/me/policy", fetch_policy, methods=["GET"], response_model=None)
router.add_api_route("/v1/devices/me/policy/ack", acknowledge_policy, methods=["POST"], status_code=204, response_model=None)
router.add_api_route("/v1/devices/me/heartbeat", heartbeat, methods=["POST"], status_code=204, response_model=None)
router.add_api_route("/v1/devices/me/events", ingest_events, methods=["POST"], status_code=202, response_model=None)
router.add_api_route("/v1/devices/me/inventory", ingest_inventory, methods=["POST"], status_code=202, response_model=None)
router.add_api_route("/v1/devices/me/requests", create_request, methods=["POST"], status_code=201, response_model=None)
router.add_api_route("/v1/devices/me/push-tokens", register_device_push_token, methods=["POST"], status_code=204, response_model=None)
