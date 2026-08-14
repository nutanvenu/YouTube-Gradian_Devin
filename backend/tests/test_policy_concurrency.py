import asyncio
from copy import deepcopy

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
