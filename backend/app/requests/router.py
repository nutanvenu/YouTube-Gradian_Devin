# ruff: noqa: E501
from fastapi import APIRouter

from ..api import route_handlers as handlers

router = APIRouter()
router.add_api_route("/v1/families/{family_id}/requests", handlers.list_requests, methods=["GET"], response_model=None)
router.add_api_route("/v1/families/{family_id}/requests/{request_id}/approve", handlers.approve_request, methods=["POST"], response_model=None)
router.add_api_route("/v1/families/{family_id}/requests/{request_id}/deny", handlers.deny_request, methods=["POST"], response_model=None)
