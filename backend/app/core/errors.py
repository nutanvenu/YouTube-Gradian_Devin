import logging

from fastapi import Request
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


async def internal_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error", exc_info=exc)
    return error_response(
        "INTERNAL_ERROR", "An internal error occurred", status.HTTP_500_INTERNAL_SERVER_ERROR
    )
