import asyncio
import json
from copy import deepcopy

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.children.models import ChildProfile
from app.families.models import FamilyGuardian
from app.policies.models import PolicyBundle
from app.policies.service import create_next_bundle


async def _mutate(url: str, child_id, parent_id, marker: str) -> int:
    engine = create_async_engine(url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            current = await session.scalar(
                select(PolicyBundle).where(
                    PolicyBundle.child_profile_id == child_id,
                    PolicyBundle.is_current.is_(True),
                )
            )
            assert current is not None
            policy = deepcopy(current.new_value)
            policy["signature"] = ""
            policy["family_id"] = marker
            bundle = await create_next_bundle(
                session,
                child_id,
                parent_id,
                policy,
                {"marker": marker},
            )
            await session.commit()
            return bundle.policy_version
    finally:
        await engine.dispose()


async def _ids(database_session, child_id):
    child = await database_session.get(ChildProfile, child_id)
    assert child is not None
    guardian = await database_session.scalar(
        select(FamilyGuardian).where(FamilyGuardian.family_id == child.family_id)
    )
    assert guardian is not None
    return child.id, guardian.parent_id


async def test_concurrent_mutations_produce_distinct_monotonic_versions(
    test_database_url, parent_a, database_session
) -> None:
    child_id, parent_id = await _ids(database_session, parent_a.child_id)
    versions = await asyncio.gather(
        _mutate(test_database_url, child_id, parent_id, "mutation-a"),
        _mutate(test_database_url, child_id, parent_id, "mutation-b"),
    )
    assert sorted(versions) == [2, 3]
    rows = list(
        (
            await database_session.scalars(
                select(PolicyBundle)
                .where(PolicyBundle.child_profile_id == child_id)
                .order_by(PolicyBundle.policy_version)
            )
        ).all()
    )
    assert [row.policy_version for row in rows] == [1, 2, 3]


@pytest.mark.asyncio
async def test_concurrent_parent_mutations_keep_both_changes_in_the_signed_policy(
    client, parent_a, database_session
) -> None:
    url = (
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}"
        "/policy/mutations"
    )
    headers = {"Authorization": f"Bearer {parent_a.token}"}
    first, second = await asyncio.gather(
        client.post(
            url,
            headers={**headers, "Idempotency-Key": "concurrent-app-block"},
            json={"operation": "APP_BLOCK", "target": "com.example.blocked"},
        ),
        client.post(
            url,
            headers={**headers, "Idempotency-Key": "concurrent-domain-block"},
            json={"operation": "DOMAIN_BLOCK", "target": "blocked.example"},
        ),
    )
    assert first.status_code == second.status_code == 200
    current = await database_session.scalar(
        select(PolicyBundle).where(
            PolicyBundle.child_profile_id == parent_a.child_id,
            PolicyBundle.is_current.is_(True),
        )
    )
    assert current is not None
    assert {rule["app_ref"] for rule in current.new_value["app_rules"]} == {"com.example.blocked"}
    assert {rule["domain"] for rule in current.new_value["domain_rules"]} == {"blocked.example"}


@pytest.mark.asyncio
async def test_same_key_concurrent_policy_mutation_replays_one_result_without_unique_race(
    client, parent_a, database_session
) -> None:
    url = (
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}"
        "/policy/mutations"
    )
    headers = {
        "Authorization": f"Bearer {parent_a.token}",
        "Idempotency-Key": "same-policy-mutation",
    }
    body = {"operation": "APP_BLOCK", "target": "com.example.same-key"}
    first, second = await asyncio.gather(
        client.post(url, headers=headers, json=body),
        client.post(url, headers=headers, json=body),
    )
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    current = await database_session.scalar(
        select(PolicyBundle).where(
            PolicyBundle.child_profile_id == parent_a.child_id,
            PolicyBundle.is_current.is_(True),
        )
    )
    assert current is not None
    assert current.policy_version == 2
    assert [rule["app_ref"] for rule in current.new_value["app_rules"]] == [
        "com.example.same-key"
    ]

    changed = await client.post(
        url,
        headers=headers,
        json={"operation": "APP_BLOCK", "target": "com.example.other"},
    )
    assert changed.status_code == 409


@pytest.mark.asyncio
async def test_policy_idempotency_key_is_bound_to_the_child_resource(client, parent_a) -> None:
    headers = {
        "Authorization": f"Bearer {parent_a.token}",
        "Idempotency-Key": "same-key-different-child",
    }
    second_child = await client.post(
        f"/v1/families/{parent_a.family_id}/children",
        headers={"Authorization": f"Bearer {parent_a.token}"},
        json={"name": "Taylor", "date_of_birth": "2015-08-15", "timezone": "UTC"},
    )
    assert second_child.status_code == 201, second_child.text
    body = {"operation": "APP_BLOCK", "target": "com.example.same"}
    first = await client.post(
        f"/v1/families/{parent_a.family_id}/children/{parent_a.child_id}/policy/mutations",
        headers=headers,
        json=body,
    )
    assert first.status_code == 200
    cross_resource = await client.post(
        f"/v1/families/{parent_a.family_id}/children/{second_child.json()['id']}/policy/mutations",
        headers=headers,
        json=body,
    )
    assert cross_resource.status_code == 409


@pytest.mark.asyncio
async def test_approval_and_policy_mutation_do_not_drop_each_others_update(
    client, paired_device, database_session
) -> None:
    request_body = json.dumps(
        {"request_type": "UNBLOCK_APP", "subject": "com.example.reader"},
        separators=(",", ":"),
    ).encode()
    created = await client.post(
        "/v1/devices/me/requests",
        content=request_body,
        headers=paired_device.signed_headers("/v1/devices/me/requests", request_body),
    )
    assert created.status_code == 201, created.text
    parent_headers = {"Authorization": f"Bearer {paired_device.parent.token}"}
    mutate_url = (
        f"/v1/families/{paired_device.parent.family_id}/children/"
        f"{paired_device.parent.child_id}/policy/mutations"
    )
    approval_url = (
        f"/v1/families/{paired_device.parent.family_id}/requests/"
        f"{created.json()['id']}/approve"
    )
    mutation, approval = await asyncio.gather(
        client.post(
            mutate_url,
            headers={**parent_headers, "Idempotency-Key": "concurrent-app-rule"},
            json={"operation": "APP_BLOCK", "target": "com.example.video"},
        ),
        client.post(
            approval_url,
            headers={**parent_headers, "Idempotency-Key": "concurrent-approval"},
            json={"reason": "Approved"},
        ),
    )
    assert mutation.status_code == approval.status_code == 200
    current = await database_session.scalar(
        select(PolicyBundle).where(
            PolicyBundle.child_profile_id == paired_device.parent.child_id,
            PolicyBundle.is_current.is_(True),
        )
    )
    assert current is not None
    assert any(rule["app_ref"] == "com.example.video" for rule in current.new_value["app_rules"])
    assert current.new_value["temporary_overrides"][-1]["target_ref"] == "com.example.reader"


@pytest.mark.asyncio
async def test_two_approvals_are_idempotent_and_create_one_override(
    client, paired_device, database_session
) -> None:
    request_body = json.dumps(
        {"request_type": "UNBLOCK_APP", "subject": "com.example.reader"},
        separators=(",", ":"),
    ).encode()
    created = await client.post(
        "/v1/devices/me/requests",
        content=request_body,
        headers=paired_device.signed_headers("/v1/devices/me/requests", request_body),
    )
    assert created.status_code == 201, created.text
    url = (
        f"/v1/families/{paired_device.parent.family_id}/requests/"
        f"{created.json()['id']}/approve"
    )
    headers = {"Authorization": f"Bearer {paired_device.parent.token}"}
    first, second = await asyncio.gather(
        client.post(url, headers=headers, json={"reason": "Approved"}),
        client.post(url, headers=headers, json={"reason": "Approved"}),
    )
    assert first.status_code == second.status_code == 200
    current = await database_session.scalar(
        select(PolicyBundle).where(
            PolicyBundle.child_profile_id == paired_device.parent.child_id,
            PolicyBundle.is_current.is_(True),
        )
    )
    assert current is not None
    assert current.policy_version == 2
    overrides = [
        item
        for item in current.new_value["temporary_overrides"]
        if item["rule_id"] == f"request-{created.json()['id']}"
    ]
    assert len(overrides) == 1


@pytest.mark.asyncio
async def test_same_key_concurrent_approval_replays_one_result_and_one_override(
    client, paired_device, database_session
) -> None:
    request_body = json.dumps(
        {"request_type": "UNBLOCK_APP", "subject": "com.example.reader"},
        separators=(",", ":"),
    ).encode()
    created = await client.post(
        "/v1/devices/me/requests",
        content=request_body,
        headers=paired_device.signed_headers("/v1/devices/me/requests", request_body),
    )
    assert created.status_code == 201, created.text
    url = (
        f"/v1/families/{paired_device.parent.family_id}/requests/"
        f"{created.json()['id']}/approve"
    )
    headers = {
        "Authorization": f"Bearer {paired_device.parent.token}",
        "Idempotency-Key": "same-request-approval",
    }
    first, second = await asyncio.gather(
        client.post(url, headers=headers, json={"reason": "Approved"}),
        client.post(url, headers=headers, json={"reason": "Approved"}),
    )
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    current = await database_session.scalar(
        select(PolicyBundle).where(
            PolicyBundle.child_profile_id == paired_device.parent.child_id,
            PolicyBundle.is_current.is_(True),
        )
    )
    assert current is not None
    assert current.policy_version == 2
    overrides = [
        item
        for item in current.new_value["temporary_overrides"]
        if item["rule_id"] == f"request-{created.json()['id']}"
    ]
    assert len(overrides) == 1

    different_reason = await client.post(
        url,
        headers=headers,
        json={"reason": "Changed explanation"},
    )
    assert different_reason.status_code == 409
