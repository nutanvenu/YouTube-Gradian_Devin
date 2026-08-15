from fastapi import APIRouter

from ..api.handler_support import (
    UUID,
    AsyncSession,
    Depends,
    Device,
    HTTPException,
    HTTPRequest,
    Parent,
    current_device,
    current_parent,
    family_for_parent,
    get_session,
    select,
    status,
    verify_device_request_headers,
)
from ..children.models import ChildProfile
from .schemas import (
    ReputationClassificationOut,
    ReputationClassifyIn,
    ReputationEntryOut,
    ReputationStatusOut,
    ReputationSyncOut,
)
from .service import (
    classify_and_store,
    current_entries,
    normalize_domain_identifier,
    sync_for_version,
)

router = APIRouter()


async def device_reputation(
    version: int = 0,
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> ReputationSyncOut:
    current, bundle, deltas = await sync_for_version(session, version)
    await session.commit()
    return ReputationSyncOut(current_version=current, bundle=bundle, deltas=deltas)


async def classify_domain(
    body: ReputationClassifyIn,
    request: HTTPRequest,
    device: Device = Depends(current_device),
    session: AsyncSession = Depends(get_session),
) -> ReputationClassificationOut:
    await verify_device_request_headers(request, device, session)
    try:
        identifier = normalize_domain_identifier(body.identifier)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    verdict, reason = await classify_and_store(session, identifier)
    await session.commit()
    return ReputationClassificationOut(
        identifier=identifier,
        verdict=verdict,
        state="RESOLVED",
        reason=reason,
    )


async def parent_reputation(
    family_id: UUID,
    child_id: UUID,
    parent: Parent = Depends(current_parent),
    session: AsyncSession = Depends(get_session),
) -> ReputationStatusOut:
    await family_for_parent(session, parent, family_id)
    child = await session.scalar(
        select(ChildProfile).where(
            ChildProfile.id == child_id,
            ChildProfile.family_id == family_id,
        )
    )
    if child is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Child not found")
    entries = await current_entries(session)
    await session.commit()
    return ReputationStatusOut(
        current_version=max((entry.bundle_version for entry in entries), default=0),
        entries=[ReputationEntryOut.model_validate(entry) for entry in entries],
    )


router.add_api_route(
    "/v1/devices/me/reputation",
    device_reputation,
    methods=["GET"],
    response_model=ReputationSyncOut,
)
router.add_api_route(
    "/v1/devices/me/reputation/classify",
    classify_domain,
    methods=["POST"],
    response_model=ReputationClassificationOut,
)
router.add_api_route(
    "/v1/families/{family_id}/children/{child_id}/reputation",
    parent_reputation,
    methods=["GET"],
    response_model=ReputationStatusOut,
)
