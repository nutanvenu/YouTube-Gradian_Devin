import logging
from collections.abc import Mapping
from typing import Protocol
from uuid import UUID

logger = logging.getLogger(__name__)


class PushSender(Protocol):
    async def send(self, recipient: UUID, payload: Mapping[str, object]) -> None: ...


class LoggingPushSender:
    async def send(self, recipient: UUID, payload: Mapping[str, object]) -> None:
        logger.info(
            "push delivery requested",
            extra={"recipient": str(recipient), "fields": list(payload)},
        )
