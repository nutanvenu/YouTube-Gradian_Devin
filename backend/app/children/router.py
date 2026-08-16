# ruff: noqa: E501
from fastapi import APIRouter

from ..api.handler_support import (
    UTC,
    UUID,
    AsyncSession,
    ChildAppInventory,
    ChildCreate,
    ChildProfile,
    ChildUpdate,
    Depends,
    Device,
    DeviceCredential,
    HTTPException,
    ObservedAppOut,
    Parent,
    age_band_for_dob,
    create_initial_bundle,
    create_next_bundle,
    current_bundle_for_update,
    current_parent,
    datetime,
    deepcopy,
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
    bundle = await create_initial_bundle(session, child.id, parent.id, child.policy_document)
    child.policy_document = bundle.new_value
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
        # Do not recreate a default document here: doing so silently erased
        # parent app/domain/routine choices. Update the current signed policy
        # under the document mutex and publish one new, verifiable version.
        current = await current_bundle_for_update(session, child.id)
        if current is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Policy is unavailable")
        policy = deepcopy(current.new_value)
        policy["signature"] = ""
        policy["age_band"] = child.age_band
        base_policy = policy.get("base_policy")
        if not isinstance(base_policy, dict):
            raise HTTPException(status.HTTP_409_CONFLICT, "Policy is invalid")
        base_policy["timezone"] = child.timezone
        policy["base_policy"] = base_policy
        bundle = await create_next_bundle(
            session,
            child.id,
            parent.id,
            policy,
            {
                "operation": "CHILD_PROFILE_UPDATE",
                "age_band": child.age_band,
                "timezone": child.timezone,
            },
        )
        child.policy_document = bundle.new_value
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


async def list_inventory(
    family_id: UUID,
    child_id: UUID,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> list[ObservedAppOut]:
    child = await read_child(family_id, child_id, parent, session)
    rows = list(
        (
            await session.scalars(
                select(ChildAppInventory)
                .where(ChildAppInventory.child_profile_id == child.id)
                .order_by(ChildAppInventory.display_name, ChildAppInventory.platform_app_id)
            )
        ).all()
    )
    return [
        ObservedAppOut(
            platform_app_id=row.platform_app_id,
            display_name=row.display_name,
            category=row.category,
            observed_at=row.observed_at,
            reviewed=row.reviewed_at is not None,
            version_name=row.version_name,
            first_seen_at=row.first_seen_at,
            last_seen_at=row.last_seen_at,
            installation_state=row.installation_state,
            capability_sources=row.capability_sources or [],
            inventory_completeness=row.inventory_completeness,
        )
        for row in rows
    ]


async def review_inventory_app(
    family_id: UUID,
    child_id: UUID,
    platform_app_id: str,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> None:
    child = await read_child(family_id, child_id, parent, session)
    row = await session.scalar(
        select(ChildAppInventory).where(
            ChildAppInventory.child_profile_id == child.id,
            ChildAppInventory.platform_app_id == platform_app_id,
        )
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Observed app not found")
    row.reviewed_at = datetime.now(UTC)
    row.reviewed_by_parent_id = parent.id
    await session.commit()

router.add_api_route("/v1/families/{family_id}/children", create_child, methods=["POST"], status_code=201, response_model=None)
router.add_api_route("/v1/families/{family_id}/children", list_children, methods=["GET"], response_model=None)
router.add_api_route("/v1/families/{family_id}/children/{child_id}", read_child, methods=["GET"], response_model=None)
router.add_api_route("/v1/families/{family_id}/children/{child_id}", update_child, methods=["PATCH"], response_model=None)
router.add_api_route("/v1/families/{family_id}/children/{child_id}", delete_child, methods=["DELETE"], status_code=204, response_model=None)
router.add_api_route("/v1/families/{family_id}/children/{child_id}/inventory", list_inventory, methods=["GET"], response_model=list[ObservedAppOut])
router.add_api_route("/v1/families/{family_id}/children/{child_id}/inventory/{platform_app_id}/review", review_inventory_app, methods=["POST"], status_code=204, response_model=None)
