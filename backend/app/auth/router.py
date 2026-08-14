# ruff: noqa: E501
from fastapi import APIRouter

from ..api import route_handlers as handlers

router = APIRouter()
router.add_api_route("/v1/auth/signup", handlers.signup, methods=["POST"], status_code=201, response_model=None)
router.add_api_route("/v1/auth/login", handlers.login, methods=["POST"], response_model=None)
router.add_api_route("/v1/auth/refresh", handlers.refresh, methods=["POST"], response_model=None)
router.add_api_route("/v1/auth/me", handlers.me, methods=["GET"], response_model=None)
router.add_api_route("/v1/auth/verification/request", handlers.request_verification, methods=["POST"], status_code=202, response_model=None)
router.add_api_route("/v1/auth/verification/confirm", handlers.confirm_verification, methods=["POST"], status_code=204, response_model=None)
router.add_api_route("/v1/auth/password-reset/request", handlers.request_password_reset, methods=["POST"], status_code=202, response_model=None)
router.add_api_route("/v1/auth/password-reset/confirm", handlers.confirm_password_reset, methods=["POST"], status_code=204, response_model=None)
router.add_api_route("/v1/auth/logout", handlers.logout, methods=["POST"], status_code=204, response_model=None)
