# ruff: noqa: E501
from fastapi import APIRouter

from ..api import route_handlers as handlers

router = APIRouter()
router.add_api_route("/v1/families/{family_id}/children/{child_id}/pairing", handlers.create_pairing, methods=["POST"], response_model=None)
router.add_api_route("/v1/devices/pair", handlers.redeem_pairing, methods=["POST"], response_model=None)
