from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .handler_support import validate_configured_signing_key


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    validate_configured_signing_key()
    yield
