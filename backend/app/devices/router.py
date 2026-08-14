# ruff: noqa: E501
from fastapi import APIRouter

from ..api import route_handlers as handlers

router = APIRouter()
router.add_api_route("/v1/devices/me/policy", handlers.fetch_policy, methods=["GET"], response_model=None)
router.add_api_route("/v1/devices/me/policy/ack", handlers.acknowledge_policy, methods=["POST"], status_code=204, response_model=None)
router.add_api_route("/v1/devices/me/heartbeat", handlers.heartbeat, methods=["POST"], status_code=204, response_model=None)
router.add_api_route("/v1/devices/me/events", handlers.ingest_events, methods=["POST"], status_code=202, response_model=None)
router.add_api_route("/v1/devices/me/requests", handlers.create_request, methods=["POST"], status_code=201, response_model=None)
router.add_api_route("/v1/devices/me/push-tokens", handlers.register_device_push_token, methods=["POST"], status_code=204, response_model=None)
