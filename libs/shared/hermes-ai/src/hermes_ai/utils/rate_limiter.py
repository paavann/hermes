import asyncio
import logging
import time


logger = logging.getLogger(__name__)


class CircuitBreakerOpenError(Exception):
    """Raised when an operation is attempted while the circuit breaker is open."""


class TbRateLimiter:
    """Token bucket rate limiter with burst control and circuit breaking."""

    def __init__(
        self,
        req_per_min: int,
        max_burst: float | None = None,
        circuit_cooldown_seconds: float = 120.0,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            req_per_min: Maximum permitted requests per minute.
            max_burst: Maximum token capacity. Defaults to req_per_min.
            circuit_cooldown_seconds: Cooldown duration in seconds when tripped.
        """
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
        """Check if circuit breaker is currently open."""
        return time.monotonic() < self._circuit_tripped_until


    def trip_circuit_breaker(self, duration: float | None = None) -> None:
        """Trip circuit breaker to halt requests for a cooldown duration.

        Args:
            duration: Optional custom cooldown in seconds.
        """
        cooldown = duration if duration is not None else self._circuit_cooldown
        self._circuit_tripped_until = time.monotonic() + cooldown
        logger.warning(
            "rate limiter circuit breaker tripped for %.1fs.",
            cooldown,
        )


    def reset_circuit_breaker(self) -> None:
        """Reset the circuit breaker."""
        self._circuit_tripped_until = 0.0


    async def acquire(self) -> None:
        """Acquire a token from the bucket, waiting if empty.

        Raises:
            CircuitBreakerOpenError: If the circuit breaker is currently open.
        """
        if self.is_circuit_open():
            raise CircuitBreakerOpenError(
                f"circuit breaker is open until {self._circuit_tripped_until}."
            )
        async with self._get_lock():
            if self.is_circuit_open():
                raise CircuitBreakerOpenError(
                    f"circuit breaker is open until {self._circuit_tripped_until}."
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
