# ruff: noqa: E501
from fastapi import APIRouter

from ..api import route_handlers as handlers

router = APIRouter()
router.add_api_route("/v1/families/{family_id}/children", handlers.create_child, methods=["POST"], status_code=201, response_model=None)
router.add_api_route("/v1/families/{family_id}/children", handlers.list_children, methods=["GET"], response_model=None)
router.add_api_route("/v1/families/{family_id}/children/{child_id}", handlers.read_child, methods=["GET"], response_model=None)
router.add_api_route("/v1/families/{family_id}/children/{child_id}", handlers.update_child, methods=["PATCH"], response_model=None)
router.add_api_route("/v1/families/{family_id}/children/{child_id}", handlers.delete_child, methods=["DELETE"], status_code=204, response_model=None)
