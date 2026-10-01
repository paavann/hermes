import asyncio
import logging
import time


logger = logging.getLogger(__name__)


class TbRateLimiter:
    def __init__(self, req_per_min: int) -> None:
        self._rpm = req_per_min
        self._max_tokens = float(req_per_min)
        self._tokens = float(req_per_min)
        self._refill_rate = req_per_min / 60.0
        self._last_refill = time.monotonic()
        self._lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self._max_tokens,
            self._tokens + elapsed * self._refill_rate,
        )
        self._last_refill = now

    async def acquire(self) -> None:
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
    def req_per_min(self) -> int:
        return self._rpm
