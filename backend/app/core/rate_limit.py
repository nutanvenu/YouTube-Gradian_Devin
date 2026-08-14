from collections import defaultdict
from time import monotonic

from fastapi import HTTPException, status


class InProcessRateLimiter:
    def __init__(self) -> None:
        self._requests: defaultdict[str, list[float]] = defaultdict(list)

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = monotonic()
        recent = [value for value in self._requests[key] if now - value < window_seconds]
        if len(recent) >= limit:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded")
        recent.append(now)
        self._requests[key] = recent
