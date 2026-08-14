# ruff: noqa: E501
from fastapi import APIRouter

from ..api import route_handlers as handlers

router = APIRouter()
router.add_api_route("/v1/families", handlers.create_family, methods=["POST"], status_code=201, response_model=None)
router.add_api_route("/v1/families/{family_id}", handlers.read_family, methods=["GET"], response_model=None)
router.add_api_route("/v1/families/{family_id}/guardians", handlers.list_guardians, methods=["GET"], response_model=None)
router.add_api_route("/v1/families/{family_id}/guardians/invite", handlers.invite_guardian, methods=["POST"], status_code=202, response_model=None)
router.add_api_route("/v1/families/guardians/accept", handlers.accept_guardian, methods=["POST"], status_code=204, response_model=None)
router.add_api_route("/v1/families/{family_id}/devices/{device_id}/revoke", handlers.revoke_device, methods=["POST"], status_code=204, response_model=None)
