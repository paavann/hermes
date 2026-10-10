"""Tests for the token-bucket rate limiter from hermes_ai."""

import asyncio
import time
from hermes_ai import TbRateLimiter


def test_rate_limiter_allows_burst_up_to_limit() -> None:
    """The limiter should allow an initial burst equal to the bucket size."""

    async def _run() -> None:
        limiter = TbRateLimiter(req_per_min=60)
        start = time.monotonic()
        for _ in range(60):
            await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 2.0

    asyncio.run(_run())


def test_rate_limiter_throttles_after_burst() -> None:
    """After the initial burst is exhausted, acquire() should wait."""

    async def _run() -> None:
        limiter = TbRateLimiter(req_per_min=60)
        for _ in range(60):
            await limiter.acquire()
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.8, f"Expected ~1s wait, got {elapsed:.2f}s"

    asyncio.run(_run())


def test_rate_limiter_refills_over_time() -> None:
    """Tokens should refill after time has passed."""

    async def _run() -> None:
        limiter = TbRateLimiter(req_per_min=60)
        for _ in range(60):
            await limiter.acquire()
        await asyncio.sleep(2.0)
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.5

    asyncio.run(_run())


def test_rate_limiter_property() -> None:
    """The req_per_min property should return the configured value."""
    limiter = TbRateLimiter(req_per_min=15)
    assert limiter.req_per_min == 15
