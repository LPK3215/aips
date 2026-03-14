from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass
from threading import Lock

from app.core.config import (
    RATE_LIMIT_ARCHIVE_REQUESTS,
    RATE_LIMIT_HEAVY_REQUESTS,
    RATE_LIMIT_UPLOAD_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
)


@dataclass
class RateLimitBucket:
    limit: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    reset_after_seconds: int


class RateLimitService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests: dict[tuple[str, str], deque[float]] = {}
        self.buckets: dict[str, RateLimitBucket] = {
            "upload": RateLimitBucket(
                limit=RATE_LIMIT_UPLOAD_REQUESTS,
                window_seconds=RATE_LIMIT_WINDOW_SECONDS,
            ),
            "heavy": RateLimitBucket(
                limit=RATE_LIMIT_HEAVY_REQUESTS,
                window_seconds=RATE_LIMIT_WINDOW_SECONDS,
            ),
            "archive": RateLimitBucket(
                limit=RATE_LIMIT_ARCHIVE_REQUESTS,
                window_seconds=RATE_LIMIT_WINDOW_SECONDS,
            ),
        }
        self._last_global_prune_at = 0.0

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()
            self._last_global_prune_at = 0.0

    def check(self, bucket_name: str, identifier: str, *, now: float | None = None) -> RateLimitDecision:
        bucket = self.buckets[bucket_name]
        current = time.monotonic() if now is None else now
        key = (bucket_name, identifier)

        with self._lock:
            if current - self._last_global_prune_at >= bucket.window_seconds:
                self._prune_all(current)

            timestamps = self._requests.get(key)
            if timestamps is None:
                timestamps = deque()
                self._requests[key] = timestamps
            self._prune(timestamps, current, bucket.window_seconds)

            if len(timestamps) >= bucket.limit:
                oldest = timestamps[0]
                reset_after = max(1, math.ceil(bucket.window_seconds - (current - oldest)))
                return RateLimitDecision(
                    allowed=False,
                    limit=bucket.limit,
                    remaining=0,
                    reset_after_seconds=reset_after,
                )

            timestamps.append(current)
            oldest = timestamps[0]
            reset_after = max(1, math.ceil(bucket.window_seconds - (current - oldest)))
            return RateLimitDecision(
                allowed=True,
                limit=bucket.limit,
                remaining=max(0, bucket.limit - len(timestamps)),
                reset_after_seconds=reset_after,
            )

    def _prune_all(self, now: float) -> None:
        for (bucket_name, identifier), timestamps in list(self._requests.items()):
            bucket = self.buckets.get(bucket_name)
            if bucket is None:
                self._requests.pop((bucket_name, identifier), None)
                continue

            self._prune(timestamps, now, bucket.window_seconds)
            if not timestamps:
                self._requests.pop((bucket_name, identifier), None)

        self._last_global_prune_at = now

    def _prune(self, timestamps: deque[float], now: float, window_seconds: int) -> None:
        cutoff = now - window_seconds
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()


rate_limit_service = RateLimitService()
