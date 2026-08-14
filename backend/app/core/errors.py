import logging

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette import status

logger = logging.getLogger(__name__)


def error_response(code: str, message: str, http_status: int) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"error": {"code": code, "message": message}},
    )


async def validation_error_handler(
    _request: Request, _exc: Exception
) -> JSONResponse:
    return error_response(
        "VALIDATION_ERROR", "Request validation failed", status.HTTP_422_UNPROCESSABLE_ENTITY
    )


def http_error_code(status_code: int) -> str:
    return {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "AUTHENTICATION_ERROR",
        status.HTTP_403_FORBIDDEN: "AUTHORIZATION_ERROR",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_409_CONFLICT: "CONFLICT",
        status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
    }.get(status_code, "REQUEST_ERROR")


async def http_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, HTTPException):
        return error_response("REQUEST_ERROR", "Request failed", status.HTTP_400_BAD_REQUEST)
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return error_response(http_error_code(exc.status_code), message, exc.status_code)


async def internal_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error", exc_info=exc)
    return error_response(
        "INTERNAL_ERROR", "An internal error occurred", status.HTTP_500_INTERNAL_SERVER_ERROR
    )
