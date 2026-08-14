"""FastAPI application composition."""

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from ..auth.router import router as auth_router
from ..children.router import router as children_router
from ..devices.router import router as devices_router
from ..events.router import router as events_router
from ..families.router import router as families_router
from ..health.router import router as health_router
from ..pairing.router import router as pairing_router
from ..policies.router import router as policies_router
from ..push.router import router as push_router
from ..requests.router import router as requests_router
from .route_handlers import (
    http_exception_handler,
    internal_error_handler,
    lifespan,
    notifier,
    validation_error_handler,
)

app = FastAPI(title="Guardian API", version="0.1.0", lifespan=lifespan)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, internal_error_handler)

for router in (
    auth_router,
    families_router,
    children_router,
    devices_router,
    pairing_router,
    policies_router,
    events_router,
    health_router,
    requests_router,
    push_router,
):
    app.include_router(router)
__all__ = ["app", "notifier"]
