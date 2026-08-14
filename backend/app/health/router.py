# ruff: noqa: E501
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..api import route_handlers as handlers
from ..core.db import get_session
from ..policies.signing import validate_configured_signing_key

router = APIRouter()
router.add_api_route("/health", lambda: {"status": "ok"}, methods=["GET"])
router.add_api_route("/livez", lambda: {"status": "ok"}, methods=["GET"])


async def readiness(session: AsyncSession = Depends(get_session)) -> JSONResponse | dict[str, str]:
    try:
        validate_configured_signing_key()
        await session.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}


router.add_api_route("/readiness", readiness, methods=["GET"], response_model=None)
router.add_api_route("/readyz", readiness, methods=["GET"], response_model=None)
router.add_api_route("/v1/families/{family_id}/health", handlers.family_health, methods=["GET"], response_model=None)
