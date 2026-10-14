"""In-memory rate limit. One process only; put a shared store in front of several workers."""

import time
from collections import defaultdict, deque

WINDOW_SECONDS = 60
MAX_REQUESTS = 10


class RateLimiter:
    def __init__(self, limit: int = MAX_REQUESTS, window: int = WINDOW_SECONDS) -> None:
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self._hits[key]
        while bucket and now - bucket[0] > self.window:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(now)
        return True


limiter = RateLimiter()