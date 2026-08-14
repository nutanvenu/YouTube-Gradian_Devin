# ruff: noqa: E501
from fastapi import APIRouter

from ..api import route_handlers as handlers

router = APIRouter()
router.add_api_route("/v1/me/push-tokens", handlers.register_push_token, methods=["POST"], status_code=204, response_model=None)
