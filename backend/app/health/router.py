# ruff: noqa: E501
from fastapi import APIRouter

from ..api import route_handlers as handlers

router = APIRouter()
router.add_api_route("/v1/families/{family_id}/health", handlers.family_health, methods=["GET"], response_model=None)
