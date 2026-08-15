# ruff: noqa: E501
from fastapi import APIRouter

from ..api.handler_support import (
    UTC,
    UUID,
    AsyncSession,
    ChildProfile,
    Depends,
    Header,
    HTTPException,
    Parent,
    PolicyBundle,
    PolicyMutationIn,
    broadcaster,
    configured_trusted_public_keys,
    create_next_bundle,
    current_parent,
    datetime,
    deepcopy,
    family_for_parent,
    get_session,
    get_settings,
    payload_hash,
    policy_mapping,
    policy_records,
    replay_or_conflict,
    save_result,
    secrets,
    select,
    signer,
    status,
)
from .temporary import build_screen_time_override

router = APIRouter()


def _replace_rule(
    records: list[dict[str, object]],
    field: str,
    target: object,
    replacement: dict[str, object],
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    replaced = False
    for record in records:
        if record.get(field) == target:
            if not replaced:
                result.append(replacement)
                replaced = True
            continue
        result.append(record)
    if not replaced:
        result.append(replacement)
    return result


async def policy_public_key() -> dict[str, object]:
    settings = get_settings()
    trusted = configured_trusted_public_keys()
    if settings.policy_key_id not in trusted:
        trusted[settings.policy_key_id] = signer.public_key()
    return {
        "key_id": settings.policy_key_id,
        "public_key": trusted[settings.policy_key_id],
        "trusted_public_keys": trusted,
    }

async def mutate_policy(
    family_id: UUID,
    child_id: UUID,
    body: PolicyMutationIn,
    parent: Parent = Depends(current_parent),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    await family_for_parent(session, parent, family_id)
    child = await session.scalar(
        select(ChildProfile).where(ChildProfile.id == child_id, ChildProfile.family_id == family_id)
    )
    if child is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Child not found")
    digest = payload_hash(body.model_dump(mode="json"))
    if idempotency_key is not None:
        replay = await replay_or_conflict(session, "policy_mutation", idempotency_key, digest)
        if replay is not None:
            return replay.response_body
    current = await session.scalar(
        select(PolicyBundle).where(
            PolicyBundle.child_profile_id == child_id, PolicyBundle.is_current.is_(True)
        )
    )
    if current is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Policy is unavailable")
    policy = deepcopy(current.new_value)
    policy["signature"] = ""
    operation = body.operation
    rule_id = f"{operation.lower()}-{UUID(int=secrets.randbits(128))}"
    if operation.startswith("APP_"):
        action = {
            "APP_ALLOW": "ALLOW",
            "APP_BLOCK": "BLOCK",
            "APP_UNLIMITED": "UNLIMITED",
            "APP_DAILY_MINUTES": "LIMIT",
            "APP_SCHEDULE": "SCHEDULE",
        }[operation]
        rule: dict[str, object] = {"rule_id": rule_id, "app_ref": body.target, "action": action}
        if action == "LIMIT":
            if not isinstance(body.value, int) or body.value < 0:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Daily minutes required")
            rule["daily_minutes"] = body.value
        if action == "SCHEDULE":
            if not isinstance(body.value, dict):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Schedule required")
            rule["schedule"] = body.value
        policy["app_rules"] = _replace_rule(
            policy_records(policy, "app_rules"), "app_ref", body.target, rule
        )
    elif operation in {"DOMAIN_ALLOW", "DOMAIN_BLOCK"}:
        rule = {
            "rule_id": rule_id,
            "domain": body.target,
            "action": "ALLOW" if operation == "DOMAIN_ALLOW" else "BLOCK",
        }
        policy["domain_rules"] = _replace_rule(
            policy_records(policy, "domain_rules"), "domain", body.target, rule
        )
    elif operation in {"CATEGORY_DAILY_MINUTES", "WEB_CATEGORY_ALLOW", "WEB_CATEGORY_BLOCK"}:
        if operation == "WEB_CATEGORY_ALLOW":
            action = "ALLOW"
        elif operation == "WEB_CATEGORY_BLOCK":
            action = "BLOCK"
        else:
            action = "LIMIT"
        if not isinstance(body.value, int) or body.value < 0:
            if operation == "CATEGORY_DAILY_MINUTES":
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Daily minutes required")
        rule = {
            "rule_id": rule_id,
            "category": body.target,
            "action": action,
            **({"daily_minutes": body.value} if action == "LIMIT" else {}),
        }
        policy["category_rules"] = _replace_rule(
            policy_records(policy, "category_rules"), "category", body.target, rule
        )
    elif operation == "UNKNOWN_DOMAIN_POLICY" or operation == "UNKNOWN_APP_POLICY":
        allowed = (
            {"BLOCK", "BLOCK_WHILE_CLASSIFYING", "ALLOW_WHILE_CLASSIFYING", "ALLOW_AND_NOTIFY"}
            if operation == "UNKNOWN_DOMAIN_POLICY"
            else {"BLOCK", "LIMIT_AND_NOTIFY", "ALLOW_AND_NOTIFY", "ALLOW"}
        )
        if body.value not in allowed:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid unknown policy")
        field = (
            "unknown_domain_policy"
            if operation == "UNKNOWN_DOMAIN_POLICY"
            else "unknown_app_policy"
        )
        base = policy_mapping(policy, "base_policy")
        base[field] = body.value
        policy["base_policy"] = base
    elif operation in {
        "ROUTINE_CREATE",
        "ROUTINE_UPDATE",
        "ROUTINE_DELETE",
        "ROUTINE_ACTIVATE",
        "ROUTINE_DEACTIVATE",
    }:
        routines = policy_records(policy, "routines")
        if operation == "ROUTINE_DELETE":
            routines = [routine for routine in routines if routine.get("routine_id") != body.target]
        elif operation in {"ROUTINE_ACTIVATE", "ROUTINE_DEACTIVATE"}:
            routine = next(
                (item for item in routines if item.get("routine_id") == body.target),
                None,
            )
            if routine is None or routine.get("kind") != "MANUAL":
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Manual routine not found")
            base = policy_mapping(policy, "base_policy")
            base["current_manual_routine_id"] = (
                body.target if operation == "ROUTINE_ACTIVATE" else None
            )
            policy["base_policy"] = base
        elif not isinstance(body.value, dict):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Routine value required")
        elif operation == "ROUTINE_CREATE":
            routines.append(body.value)
        else:
            replaced = False
            for index, routine in enumerate(routines):
                if routine.get("routine_id") == body.target:
                    routines[index] = body.value
                    replaced = True
            if not replaced:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Routine not found")
        policy["routines"] = routines
    elif operation == "COMMUNICATION_ENABLED":
        if not isinstance(body.value, bool):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Communication setting requires a boolean")
        communication = policy_mapping(policy, "communication_safety")
        communication["enabled"] = body.value
        policy["communication_safety"] = communication
    elif operation == "COMMUNICATION_SENSITIVITY":
        if body.value not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid sensitivity")
        communication = policy_mapping(policy, "communication_safety")
        communication["severity_threshold"] = body.value
        policy["communication_safety"] = communication
    elif operation == "TEMPORARY_EXCEPTION":
        if body.expires_at is None or body.expires_at <= datetime.now(UTC):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Future expiry required")
        policy["temporary_overrides"] = [
            *policy_records(policy, "temporary_overrides"),
            {
                "rule_id": rule_id,
                "target_kind": "DOMAIN",
                "target_ref": body.target,
                "action": "ALLOW",
                "starts_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "expires_at": body.expires_at.isoformat().replace("+00:00", "Z"),
            },
        ]
    elif operation == "TEMPORARY_SCREEN_TIME":
        if not isinstance(body.value, int) or body.value <= 0:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Additional minutes required")
        if body.expires_at is None or body.expires_at <= datetime.now(UTC):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Future expiry required")
        policy["temporary_overrides"] = [
            *policy_records(policy, "temporary_overrides"),
            build_screen_time_override(
                policy,
                body.target,
                body.value,
                rule_id,
                datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                body.expires_at.isoformat().replace("+00:00", "Z"),
            ),
        ]
    elif operation in {"PAUSE_INTERNET", "RESUME_INTERNET"}:
        routines = [
            routine for routine in policy_records(policy, "routines")
            if routine.get("routine_id") != "pause-internet"
        ]
        if operation == "PAUSE_INTERNET":
            routines.append(
                {
                    "routine_id": "pause-internet",
                    "name": "Paused internet",
                    "kind": "MANUAL",
                    "blocked_categories": [],
                    "web_mode": "STRICT",
                }
            )
            base = policy_mapping(policy, "base_policy")
            base["current_manual_routine_id"] = "pause-internet"
            policy["base_policy"] = base
        else:
            base = policy_mapping(policy, "base_policy")
            base["current_manual_routine_id"] = None
            policy["base_policy"] = base
        policy["routines"] = routines
    bundle = await create_next_bundle(
        session,
        child_id,
        parent.id,
        policy,
        {"operation": operation, "target": body.target, "value": body.value},
        expires_at=body.expires_at,
    )
    child.policy_document = bundle.new_value
    result = {
        "bundle": bundle.new_value,
        "policy_version": bundle.policy_version,
        "effective_at": bundle.effective_at.isoformat(),
        "author_parent_id": str(parent.id),
        "mutation_at": bundle.created_at.isoformat(),
        "expires_at": bundle.expires_at.isoformat() if bundle.expires_at else None,
        "previous_value": bundle.previous_value,
        "new_value": bundle.new_value,
        "superseded_policy_version": bundle.policy_version - 1,
    }
    if idempotency_key is not None:
        await save_result(
            session, "policy_mutation", idempotency_key, digest, status.HTTP_200_OK, result
        )
    await session.commit()
    broadcaster.publish(
        family_id,
        {"type": "policy-version-changed", "policy_version": bundle.policy_version},
        child_id,
    )
    return result

router.add_api_route("/v1/policy/public-key", policy_public_key, methods=["GET"], response_model=None)
router.add_api_route("/v1/families/{family_id}/children/{child_id}/policy/mutations", mutate_policy, methods=["POST"], response_model=None)
