from collections import defaultdict, deque
from time import monotonic


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = monotonic()
        hits = self._hits[key]
        cutoff = now - window_seconds

        while hits and hits[0] < cutoff:
            hits.popleft()

        if len(hits) >= limit:
            return False

        hits.append(now)
        return True

    def clear(self) -> None:
        self._hits.clear()


rate_limiter = InMemoryRateLimiter()
