"""Tests for the token-bucket rate limiter."""

import asyncio
import time

from hermes_api.core.rate_limiter import TokenBucketRateLimiter


def test_rate_limiter_allows_burst_up_to_limit():
    """The limiter should allow an initial burst equal to the bucket size."""

    async def _run():
        limiter = TokenBucketRateLimiter(requests_per_minute=60)
        start = time.monotonic()
        for _ in range(60):
            await limiter.acquire()
        elapsed = time.monotonic() - start
        # 60 tokens available immediately; burst should complete quickly.
        assert elapsed < 2.0

    asyncio.run(_run())


def test_rate_limiter_throttles_after_burst():
    """After the initial burst is exhausted, acquire() should wait."""

    async def _run():
        limiter = TokenBucketRateLimiter(requests_per_minute=60)
        # Exhaust the bucket.
        for _ in range(60):
            await limiter.acquire()
        # The next acquire should block for approximately 1 second.
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.8, f"Expected ~1s wait, got {elapsed:.2f}s"

    asyncio.run(_run())


def test_rate_limiter_refills_over_time():
    """Tokens should refill after time has passed."""

    async def _run():
        limiter = TokenBucketRateLimiter(requests_per_minute=60)
        # Exhaust the bucket.
        for _ in range(60):
            await limiter.acquire()
        # Wait 2 seconds — should refill ~2 tokens at 60 rpm.
        await asyncio.sleep(2.0)
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        # Should be nearly instant since tokens have refilled.
        assert elapsed < 0.5

    asyncio.run(_run())


def test_rate_limiter_property():
    """The requests_per_minute property should return the configured value."""
    limiter = TokenBucketRateLimiter(requests_per_minute=15)
    assert limiter.requests_per_minute == 15
