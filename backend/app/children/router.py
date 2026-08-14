# ruff: noqa: E501
from fastapi import APIRouter

from ..api.handler_support import (
    UTC,
    UUID,
    AsyncSession,
    ChildCreate,
    ChildProfile,
    ChildUpdate,
    Depends,
    Device,
    DeviceCredential,
    HTTPException,
    Parent,
    age_band_for_dob,
    create_initial_bundle,
    current_parent,
    datetime,
    default_policy,
    family_for_parent,
    get_session,
    select,
    status,
    update,
    validate_timezone,
)

router = APIRouter()


async def create_child(
    family_id: UUID,
    body: ChildCreate,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> ChildProfile:
    await family_for_parent(session, parent, family_id)
    timezone = validate_timezone(body.timezone)
    band = age_band_for_dob(body.date_of_birth)
    child = ChildProfile(
        family_id=family_id,
        name=body.name,
        date_of_birth=body.date_of_birth,
        age_band=band,
        timezone=timezone,
        policy_document={},
    )
    session.add(child)
    await session.flush()
    child.policy_document = default_policy(family_id, child.id, band, timezone)
    await create_initial_bundle(session, child.id, parent.id, child.policy_document)
    await session.commit()
    await session.refresh(child)
    return child

async def list_children(
    family_id: UUID,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> list[ChildProfile]:
    await family_for_parent(session, parent, family_id)
    return list(
        (
            await session.scalars(select(ChildProfile).where(ChildProfile.family_id == family_id))
        ).all()
    )

async def read_child(
    family_id: UUID,
    child_id: UUID,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> ChildProfile:
    await family_for_parent(session, parent, family_id)
    child = await session.scalar(
        select(ChildProfile).where(ChildProfile.id == child_id, ChildProfile.family_id == family_id)
    )
    if child is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Child not found")
    return child

async def update_child(
    family_id: UUID,
    child_id: UUID,
    body: ChildUpdate,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> ChildProfile:
    child = await read_child(family_id, child_id, parent, session)
    policy_changed = False
    if body.name is not None:
        child.name = body.name
    if body.timezone is not None:
        child.timezone = validate_timezone(body.timezone)
        policy_changed = True
    if body.date_of_birth is not None:
        child.date_of_birth = body.date_of_birth
        child.age_band = age_band_for_dob(child.date_of_birth)
        policy_changed = True
    if policy_changed:
        raw_version = child.policy_document.get("policy_version", 0)
        current_version = raw_version if isinstance(raw_version, int) else 0
        child.policy_document = default_policy(
            family_id,
            child.id,
            child.age_band,
            child.timezone,
            policy_version=current_version + 1,
        )
    await session.commit()
    await session.refresh(child)
    return child

async def delete_child(
    family_id: UUID,
    child_id: UUID,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> None:
    child = await read_child(family_id, child_id, parent, session)
    devices = list(
        (
            await session.scalars(select(Device).where(Device.child_profile_id == child.id))
        ).all()
    )
    now = datetime.now(UTC)
    for device in devices:
        device.revoked_at = now
        await session.execute(
            update(DeviceCredential)
            .where(DeviceCredential.device_id == device.id)
            .values(revoked_at=now)
        )
    await session.delete(child)
    await session.commit()

router.add_api_route("/v1/families/{family_id}/children", create_child, methods=["POST"], status_code=201, response_model=None)
router.add_api_route("/v1/families/{family_id}/children", list_children, methods=["GET"], response_model=None)
router.add_api_route("/v1/families/{family_id}/children/{child_id}", read_child, methods=["GET"], response_model=None)
router.add_api_route("/v1/families/{family_id}/children/{child_id}", update_child, methods=["PATCH"], response_model=None)
router.add_api_route("/v1/families/{family_id}/children/{child_id}", delete_child, methods=["DELETE"], status_code=204, response_model=None)
