import asyncio
import time
from unittest.mock import AsyncMock, patch

from hermes_ai.client import HermesAiClient
from hermes_ai.core.config import AiConfig
from hermes_ai.models.events import ArticleInput
from hermes_ai.utils.rate_limiter import TbRateLimiter


def test_rate_limiter_property() -> None:
    limiter = TbRateLimiter(req_per_min=30)
    assert limiter.req_per_min == 30


def test_rate_limiter_acquire_burst() -> None:
    async def _run() -> None:
        limiter = TbRateLimiter(req_per_min=60)
        start = time.monotonic()
        for _ in range(10):
            await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 1.0

    asyncio.run(_run())


def test_rate_limiter_throttles_when_exhausted() -> None:
    async def _run() -> None:
        # Small limiter so we exhaust quickly: 60 rpm = 1 per sec
        limiter = TbRateLimiter(req_per_min=2)
        await limiter.acquire()
        await limiter.acquire()
        # Next acquire needs to wait ~30s normally, but let's test that tokens is < 1
        assert limiter._tokens < 1.0

    asyncio.run(_run())


def test_rate_limiter_refills() -> None:
    async def _run() -> None:
        limiter = TbRateLimiter(req_per_min=60)
        for _ in range(60):
            await limiter.acquire()
        assert limiter._tokens < 1.0
        # Wait 0.1s: at 1 token/sec, should refill ~0.1 token
        await asyncio.sleep(0.1)
        limiter._refill()
        assert limiter._tokens > 0.05

    asyncio.run(_run())


def test_client_rate_limiter_wiring() -> None:
    async def _run() -> None:
        config_no_limits = AiConfig(
            primary_model="mistral/mistral-large",
            primary_api_key="key",
        )
        client_no_limits = HermesAiClient(config_no_limits)
        assert client_no_limits.rate_limiter is None
        assert client_no_limits.embed_rate_limiter is None

        config_with_limits = AiConfig(
            primary_model="mistral/mistral-large",
            primary_api_key="key",
            embed_model="text-embedding-3-small",
            embed_api_key="key",
            rpm_limit=120,
            embed_rpm_limit=240,
        )
        client = HermesAiClient(config_with_limits)
        assert client.rate_limiter is not None
        assert client.rate_limiter.req_per_min == 120
        assert client.embed_rate_limiter is not None
        assert client.embed_rate_limiter.req_per_min == 240

        # Verify rate_limiter.acquire is called during call_llm
        with patch.object(
            client.rate_limiter, "acquire", new_callable=AsyncMock
        ) as mock_acquire:
            mock_res = AsyncMock()
            mock_res.choices = [
                AsyncMock(
                    message=AsyncMock(
                        content='{"events": [{"article_index": 0, "has_location": false, "headline": "H", "summary": "S", "category": "WORLD"}]}'
                    )
                )
            ]
            client._router.acompletion = AsyncMock(return_value=mock_res)
            articles = [ArticleInput(title="T", content="C")]
            await client.extract_events(articles)
            assert mock_acquire.called

        # Verify embed_rate_limiter.acquire is called during gen_embeddings
        with (
            patch.object(
                client.embed_rate_limiter, "acquire", new_callable=AsyncMock
            ) as mock_embed_acquire,
            patch("litellm.aembedding", new_callable=AsyncMock) as mock_embed,
        ):
            mock_embed.return_value = AsyncMock(data=[{"embedding": [0.1, 0.2]}])
            embeddings = await client.gen_embeddings(["sample"])
            assert mock_embed_acquire.called
            assert embeddings == [[0.1, 0.2]]

    asyncio.run(_run())
