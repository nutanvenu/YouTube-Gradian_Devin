from fastapi import APIRouter

from ..api import route_handlers as handlers

router = APIRouter()
router.add_api_websocket_route("/v1/ws/sync", handlers.websocket_sync)
