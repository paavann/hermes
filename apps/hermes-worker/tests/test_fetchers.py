import asyncio
import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock
import httpx
from hermes_ai.utils.rate_limiter import TbRateLimiter
from hermes_db.enums import CredibilityTier, SourceType
from hermes_db.services.source import DueSource
from hermes_worker.services.fetchers.gdelt import (
    GDELTFetcher,
    _extract_domain,
    _parse_gdelt_date,
)
from hermes_worker.services.fetchers.rss import RSSFetcher
from hermes_worker.services.fetchers.sitemap import (
    SitemapFetcher,
    _extract_article_from_html,
    _parse_sitemap_urls,
)


def test_extract_domain() -> None:
    assert _extract_domain("https://www.reuters.com") == "reuters.com"
    assert _extract_domain("https://apnews.com/hub/world-news") == "apnews.com"
    assert _extract_domain("https://www.afp.com/") == "afp.com"
    assert _extract_domain(None) == ""


def test_parse_gdelt_date() -> None:
    dt1 = _parse_gdelt_date("20261018T183000Z")
    assert dt1 == datetime(2026, 10, 18, 18, 30, 0)

    dt2 = _parse_gdelt_date("20261018183000")
    assert dt2 == datetime(2026, 10, 18, 18, 30, 0)

    assert _parse_gdelt_date("") is None
    assert _parse_gdelt_date("invalid-date") is None


def test_rss_fetcher_missing_feed_url() -> None:
    async def _run() -> None:
        fetcher = RSSFetcher()
        source = DueSource(
            id=uuid.uuid4(),
            name="No Feed Source",
            slug="no-feed",
            feed_url=None,
            source_type=SourceType.RSS,
            credibility=CredibilityTier.TIER_1,
            url="https://example.com",
        )
        articles = await fetcher.fetch_articles(source)
        assert articles == []

    asyncio.run(_run())


def test_gdelt_fetcher_success() -> None:
    async def _run() -> None:
        mock_response_data = {
            "articles": [
                {
                    "title": "Global Summit Begins in Geneva",
                    "url": "https://www.reuters.com/world/summit-geneva-123",
                    "seendate": "20261018T120000Z",
                    "sourcecountry": "Switzerland",
                    "language": "English",
                },
                {
                    "title": "Trade Deal Signed",
                    "url": "https://www.reuters.com/business/trade-deal-456",
                    "seendate": "20261018T143000Z",
                    "sourcecountry": "United States",
                    "language": "English",
                },
            ]
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_resp = AsyncMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_data
        mock_resp.raise_for_status = AsyncMock()
        mock_client.get.return_value = mock_resp

        limiter = TbRateLimiter(req_per_min=120, max_burst=10.0)
        fetcher = GDELTFetcher(rate_limiter=limiter, client=mock_client)

        source = DueSource(
            id=uuid.uuid4(),
            name="Reuters",
            slug="reuters-wire",
            feed_url=None,
            source_type=SourceType.GDELT,
            credibility=CredibilityTier.TIER_1,
            url="https://www.reuters.com",
        )

        articles = await fetcher.fetch_articles(source)

        assert len(articles) == 2
        assert articles[0].title == "Global Summit Begins in Geneva"
        assert articles[0].url == "https://www.reuters.com/world/summit-geneva-123"
        assert articles[0].published_at == datetime(2026, 10, 18, 12, 0, 0)
        assert articles[0].source_country == "Switzerland"

        assert articles[1].title == "Trade Deal Signed"
        assert articles[1].source_country == "United States"

    asyncio.run(_run())


def test_gdelt_fetcher_rate_limit_circuit_breaker() -> None:
    async def _run() -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_resp = AsyncMock(spec=httpx.Response)
        mock_resp.status_code = 429
        mock_client.get.return_value = mock_resp

        limiter = TbRateLimiter(req_per_min=120, circuit_cooldown_seconds=60.0)
        fetcher = GDELTFetcher(rate_limiter=limiter, client=mock_client)

        source = DueSource(
            id=uuid.uuid4(),
            name="Associated Press",
            slug="ap-wire",
            feed_url=None,
            source_type=SourceType.GDELT,
            credibility=CredibilityTier.TIER_1,
            url="https://apnews.com",
        )

        articles = await fetcher.fetch_articles(source)
        assert articles == []
        assert limiter.is_circuit_open()

        # Subsequent call should immediately return [] because circuit is open
        articles2 = await fetcher.fetch_articles(source)
        assert articles2 == []

    asyncio.run(_run())


def test_gdelt_fetcher_malformed_json() -> None:
    async def _run() -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_resp = AsyncMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)
        mock_resp.raise_for_status = AsyncMock()
        mock_client.get.return_value = mock_resp

        limiter = TbRateLimiter(req_per_min=120, max_burst=10.0)
        fetcher = GDELTFetcher(rate_limiter=limiter, client=mock_client)

        source = DueSource(
            id=uuid.uuid4(),
            name="AFP",
            slug="afp-wire",
            feed_url=None,
            source_type=SourceType.GDELT,
            credibility=CredibilityTier.TIER_1,
            url="https://www.afp.com",
        )

        articles = await fetcher.fetch_articles(source)
        assert articles == []

    asyncio.run(_run())


def test_parse_sitemap_urls() -> None:
    xml_sample = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url>
        <loc>https://example.com/article-1</loc>
        <lastmod>2026-10-18</lastmod>
      </url>
      <url>
        <loc>https://example.com/article-2</loc>
      </url>
      <url>
        <loc>invalid-url</loc>
      </url>
    </urlset>"""
    urls = _parse_sitemap_urls(xml_sample, max_urls=10)
    assert urls == [
        "https://example.com/article-1",
        "https://example.com/article-2",
    ]


def test_extract_article_from_html() -> None:
    html = """
    <html>
    <head>
      <title>Peace Agreement Signed</title>
      <meta name="description" content="Nations sign peace agreement.">
    </head>
    <body>
      <h1>Peace Agreement Signed</h1>
      <article>
        <p>Diplomats reached a landmark peace agreement earlier today.</p>
        <p>The deal settles long-standing territorial disputes peacefully.</p>
      </article>
    </body>
    </html>
    """
    article = _extract_article_from_html(html, "https://example.com/peace")
    assert article is not None
    assert article.title == "Peace Agreement Signed"
    assert "Diplomats reached a landmark peace agreement" in (article.content or "")
    assert article.description == "Nations sign peace agreement."


def test_sitemap_fetcher_success() -> None:
    async def _run() -> None:
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url>
            <loc>https://example.com/story-1</loc>
          </url>
        </urlset>"""

        article_html = """
        <html>
        <head>
          <title>Economy Grows in Q3</title>
          <meta name="description" content="GDP growth beats forecasts.">
        </head>
        <body>
          <article>
            <p>The gross domestic product accelerated faster than anticipated.</p>
          </article>
        </body>
        </html>
        """

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        sitemap_resp = AsyncMock(spec=httpx.Response)
        sitemap_resp.status_code = 200
        sitemap_resp.text = sitemap_xml
        sitemap_resp.raise_for_status = AsyncMock()

        html_resp = AsyncMock(spec=httpx.Response)
        html_resp.status_code = 200
        html_resp.text = article_html
        html_resp.raise_for_status = AsyncMock()

        async def _mock_get(url: str, **kwargs: object) -> AsyncMock:
            if "sitemap" in url:
                return sitemap_resp
            return html_resp

        mock_client.get.side_effect = _mock_get

        fetcher = SitemapFetcher(client=mock_client)
        source = DueSource(
            id=uuid.uuid4(),
            name="Sitemap News",
            slug="sitemap-news",
            feed_url="https://example.com/sitemap.xml",
            source_type=SourceType.SCRAPE,
            credibility=CredibilityTier.TIER_2,
            url="https://example.com",
        )

        articles = await fetcher.fetch_articles(source)
        assert len(articles) == 1
        assert articles[0].title == "Economy Grows in Q3"
        assert articles[0].url == "https://example.com/story-1"
        assert "gross domestic product" in (articles[0].content or "")

    asyncio.run(_run())


def test_sitemap_fetcher_rate_limited_or_forbidden() -> None:
    async def _run() -> None:
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url>
            <loc>https://example.com/blocked-story</loc>
          </url>
        </urlset>"""

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        sitemap_resp = AsyncMock(spec=httpx.Response)
        sitemap_resp.status_code = 200
        sitemap_resp.text = sitemap_xml
        sitemap_resp.raise_for_status = AsyncMock()

        blocked_resp = AsyncMock(spec=httpx.Response)
        blocked_resp.status_code = 403

        async def _mock_get(url: str, **kwargs: object) -> AsyncMock:
            if "sitemap" in url:
                return sitemap_resp
            return blocked_resp

        mock_client.get.side_effect = _mock_get

        fetcher = SitemapFetcher(client=mock_client)
        source = DueSource(
            id=uuid.uuid4(),
            name="Protected News",
            slug="protected-news",
            feed_url="https://example.com/sitemap.xml",
            source_type=SourceType.SCRAPE,
            credibility=CredibilityTier.TIER_2,
            url="https://example.com",
        )

        articles = await fetcher.fetch_articles(source)
        assert articles == []

    asyncio.run(_run())
