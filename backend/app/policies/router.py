# ruff: noqa: E501
from fastapi import APIRouter

from ..api import route_handlers as handlers

router = APIRouter()
router.add_api_route("/v1/policy/public-key", handlers.policy_public_key, methods=["GET"], response_model=None)
router.add_api_route("/v1/families/{family_id}/children/{child_id}/policy/mutations", handlers.mutate_policy, methods=["POST"], response_model=None)
