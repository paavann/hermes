"""Token-bucket rate limiter for controlling API request throughput.

This module provides an async-compatible rate limiter that enforces a
maximum number of requests per minute using the token-bucket algorithm.
"""

import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """A token-bucket rate limiter for async workflows.

    Enforces a maximum number of requests per minute by maintaining
    a bucket of tokens that refills at a steady rate. Callers await
    `acquire()` before making a rate-limited API call.

    Args:
        requests_per_minute: Maximum allowed requests per minute.
    """

    def __init__(self, requests_per_minute: int) -> None:
        self._rpm = requests_per_minute
        self._max_tokens = float(requests_per_minute)
        self._tokens = float(requests_per_minute)
        self._refill_rate = requests_per_minute / 60.0
        self._last_refill = time.monotonic()
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        """Lazily create the asyncio.Lock inside a running event loop."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _refill(self) -> None:
        """Refill tokens based on elapsed time since last refill."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self._max_tokens,
            self._tokens + elapsed * self._refill_rate,
        )
        self._last_refill = now

    async def acquire(self) -> None:
        """Wait until a token is available, then consume it.

        This method blocks the caller until the rate limiter has
        capacity for one more request.
        """
        async with self._get_lock():
            self._refill()
            if self._tokens < 1.0:
                wait_time = (1.0 - self._tokens) / self._refill_rate
                logger.debug(
                    f"rate limiter: waiting {wait_time:.2f}s "
                    f"for next token ({self._rpm} rpm limit)."
                )
                await asyncio.sleep(wait_time)
                self._refill()
            self._tokens -= 1.0

    @property
    def requests_per_minute(self) -> int:
        """The configured requests-per-minute limit."""
        return self._rpm
