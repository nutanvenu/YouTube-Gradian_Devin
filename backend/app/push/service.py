import hashlib
import logging
import secrets
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


def issue_action_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


def request_action_payload(
    *,
    request_id: UUID,
    request_type: str,
    subject: str | None,
    approve_token: str,
    deny_token: str,
) -> dict[str, object]:
    target = subject or request_type.replace("_", " ").lower()
    return {
        "type": "REQUEST_DECISION",
        "request_id": str(request_id),
        "title": "Guardian request",
        "body": f"Your child asked to {target}.",
        "actions": [
            {
                "id": "approve",
                "label": "Approve",
                "method": "POST",
                "path": f"/v1/push/actions/{approve_token}/approve",
            },
            {
                "id": "deny",
                "label": "Deny",
                "method": "POST",
                "path": f"/v1/push/actions/{deny_token}/deny",
            },
        ],
    }
