import json
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from app.policies.service import default_policy

SCHEMA = json.loads(
    (
        Path(__file__).parents[2]
        / "packages"
        / "policy-schema"
        / "schema"
        / "policy-bundle.schema.json"
    ).read_text()
)


@pytest.mark.parametrize(
    ("band", "expected_action", "expected_category", "budget", "unknown_domain"),
    [
        ("YOUNG_CHILD", "BLOCK", "ANONYMOUS_CHAT", 120, "BLOCK_WHILE_CLASSIFYING"),
        ("PRETEEN", "ASK_PARENT", "SOCIAL_MEDIA", 180, "BLOCK_WHILE_CLASSIFYING"),
        ("TEEN", "LIMIT", "SOCIAL_MEDIA", 240, "ALLOW_AND_NOTIFY"),
        ("OLDER_TEEN", "LIMIT", "SOCIAL_MEDIA", 300, "ALLOW_AND_NOTIFY"),
    ],
)
def test_default_policy_is_valid_and_band_specific(
    band: str,
    expected_action: str,
    expected_category: str,
    budget: int,
    unknown_domain: str,
) -> None:
    policy = default_policy(uuid4(), uuid4(), band, "UTC")
    errors = list(Draft202012Validator(SCHEMA, format_checker=FormatChecker()).iter_errors(policy))
    assert errors == []
    assert policy["issued_at"] != "1970-01-01T00:00:00Z"
    issued = datetime.fromisoformat(str(policy["issued_at"]).replace("Z", "+00:00"))
    expires = datetime.fromisoformat(str(policy["expires_soft_at"]).replace("Z", "+00:00"))
    assert expires - issued == timedelta(days=7)
    base = policy["base_policy"]
    assert base["daily_device_budget_minutes"] == budget
    assert base["unknown_domain_policy"] == unknown_domain
    matching = [
        rule
        for rule in base["default_category_rules"]
        if rule["category"] == expected_category
    ]
    assert matching and matching[0]["action"] == expected_action


def test_default_policy_versions_are_supplied_by_mutation() -> None:
    first = default_policy(uuid4(), uuid4(), "TEEN", "UTC", policy_version=4)
    second = default_policy(uuid4(), uuid4(), "TEEN", "UTC", policy_version=5)
    assert first["policy_version"] == 4
    assert second["policy_version"] == 5
