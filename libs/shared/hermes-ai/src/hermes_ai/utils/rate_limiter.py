import asyncio
import logging
import time


logger = logging.getLogger(__name__)


class CircuitBreakerOpenError(Exception):
    def __init__(
        self,
        message: str = "circuit breaker is open.",
        cooldown_remaining: float | None = None,
    ) -> None:
        super().__init__(message)
        self.cooldown_remaining = cooldown_remaining


class TbRateLimiter:
    def __init__(
        self,
        req_per_min: int,
        max_burst: float | None = None,
        circuit_cooldown_seconds: float = 120.0,
    ) -> None:
        self._rpm = req_per_min
        self._max_tokens = (
            float(max_burst) if max_burst is not None else float(req_per_min)
        )
        self._tokens = min(float(req_per_min), self._max_tokens)
        self._refill_rate = req_per_min / 60.0
        self._last_refill = time.monotonic()
        self._circuit_cooldown = circuit_cooldown_seconds
        self._circuit_tripped_until = 0.0
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

    def is_circuit_open(self) -> bool:
        return time.monotonic() < self._circuit_tripped_until

    def trip_circuit_breaker(self, duration: float | None = None) -> None:
        cooldown = duration if duration is not None else self._circuit_cooldown
        self._circuit_tripped_until = time.monotonic() + cooldown
        logger.warning(
            "rate limiter circuit breaker tripped for %.1fs.",
            cooldown,
        )

    def reset_circuit_breaker(self) -> None:
        self._circuit_tripped_until = 0.0

    async def acquire(self) -> None:
        if self.is_circuit_open():
            remaining = max(0.0, self._circuit_tripped_until - time.monotonic())
            raise CircuitBreakerOpenError(
                f"circuit breaker is open until {self._circuit_tripped_until}.",
                cooldown_remaining=remaining,
            )
        async with self._get_lock():
            if self.is_circuit_open():
                remaining = max(0.0, self._circuit_tripped_until - time.monotonic())
                raise CircuitBreakerOpenError(
                    f"circuit breaker is open until {self._circuit_tripped_until}.",
                    cooldown_remaining=remaining,
                )
            self._refill()
            if self._tokens < 1.0:
                wait_time = (1.0 - self._tokens) / self._refill_rate
                logger.debug(
                    "rate limiter: waiting %.2fs for next token (%d rpm limit).",
                    wait_time,
                    self._rpm,
                )
                await asyncio.sleep(wait_time)
                self._refill()
            self._tokens -= 1.0

    @property
    def req_per_min(self) -> int:
        return self._rpm

    @property
    def max_burst(self) -> float:
        return self._max_tokens
