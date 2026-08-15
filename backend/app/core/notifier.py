import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class Notifier(Protocol):
    async def send_email(self, recipient: str, subject: str, body: str) -> None: ...


class LoggingNotifier:
    async def send_email(self, recipient: str, subject: str, body: str) -> None:
        logger.info("Email notification queued", extra={"recipient": recipient, "subject": subject})
