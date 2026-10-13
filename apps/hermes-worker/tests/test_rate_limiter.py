import asyncio
from hermes_ai.utils.rate_limiter import TbRateLimiter


def test_rate_limiter_acquire():
    async def _test():
        limiter = TbRateLimiter(req_per_min=60)
        assert limiter.req_per_min == 60

        await limiter.acquire()
        assert limiter._tokens < 60.0

    asyncio.run(_test())
