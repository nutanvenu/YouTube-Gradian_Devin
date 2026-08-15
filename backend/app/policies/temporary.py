from collections.abc import Mapping

from ..reputation.service import normalize_domain_identifier


def _records(policy: Mapping[str, object], key: str) -> list[dict[str, object]]:
    value = policy.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _minutes(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def build_screen_time_override(
    policy: Mapping[str, object],
    target: str | None,
    additional_minutes: int,
    rule_id: str,
    starts_at: str,
    expires_at: str,
) -> dict[str, object]:
    app_rule = next(
        (
            rule
            for rule in reversed(_records(policy, "app_rules"))
            if rule.get("app_ref") == target
        ),
        None,
    )
    if app_rule is not None:
        target_kind = "APP"
        target_ref = str(target)
        existing_minutes = _minutes(app_rule.get("daily_minutes"))
    else:
        target_kind = "DEVICE"
        target_ref = "device"
        base_policy = policy.get("base_policy")
        base = base_policy if isinstance(base_policy, dict) else {}
        existing_minutes = _minutes(base.get("daily_device_budget_minutes"))
    return {
        "rule_id": rule_id,
        "target_kind": target_kind,
        "target_ref": target_ref,
        "action": "LIMIT",
        "daily_minutes": existing_minutes + additional_minutes,
        "starts_at": starts_at,
        "expires_at": expires_at,
    }


def build_more_time_override(
    policy: Mapping[str, object],
    subject: str | None,
    additional_minutes: int,
    rule_id: str,
    starts_at: str,
    expires_at: str,
) -> dict[str, object]:
    override = build_screen_time_override(
        policy, subject, additional_minutes, rule_id, starts_at, expires_at
    )
    if override["target_kind"] == "APP":
        return override
    try:
        domain = normalize_domain_identifier(subject or "")
    except ValueError:
        return override
    return {
        "rule_id": rule_id,
        "target_kind": "DOMAIN",
        "target_ref": domain,
        "action": "ALLOW",
        "starts_at": starts_at,
        "expires_at": expires_at,
    }
