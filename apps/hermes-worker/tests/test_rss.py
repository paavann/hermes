import asyncio
import time
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from hermes_db.enums import CredibilityTier, SourceType
from hermes_db.services.source import DueSource
from hermes_worker.services.fetchers.base import (
    ParsedArticle,
    _truncate_to_words,
)
from hermes_worker.services.fetchers.rss import (
    RSSFetcher,
    _extract_content,
    _parse_date,
    fetch_feed,
)


class TestParsedArticleModel:
    def test_text_for_ai_prefers_content_over_description(self):
        art = ParsedArticle(
            title="Headline",
            url="https://example.com/1",
            description="Short description",
            content="Detailed article content that has more context.",
        )
        assert art.text_for_ai == "Detailed article content that has more context."

    def test_text_for_ai_falls_back_to_description(self):
        art = ParsedArticle(
            title="Headline",
            url="https://example.com/1",
            description="Fallback description",
            content=None,
        )
        assert art.text_for_ai == "Fallback description"

    def test_text_for_ai_truncates_long_content(self):
        long_content = "word " * 600
        art = ParsedArticle(
            title="Headline",
            url="https://example.com/1",
            description="Short",
            content=long_content,
        )
        words = art.text_for_ai.split()
        assert len(words) == 500
        assert words[-1].endswith("...")


class TestRssHelpers:
    def test_truncate_to_words(self):
        short = "one two three"
        assert _truncate_to_words(short, 5) == "one two three"

        long_txt = "a b c d e f g"
        truncated = _truncate_to_words(long_txt, 3)
        assert truncated == "a b c..."

    def test_parse_date_valid(self):
        time_tuple = time.strptime("2026-10-03 12:00:00", "%Y-%m-%d %H:%M:%S")
        entry = {"published_parsed": time_tuple}
        parsed = _parse_date(entry)
        assert parsed == datetime(2026, 10, 3, 12, 0, 0, tzinfo=UTC)

    def test_parse_date_missing_or_invalid(self):
        assert _parse_date({}) is None
        assert _parse_date({"published_parsed": None}) is None
        assert _parse_date({"published_parsed": "invalid"}) is None

    def test_extract_content_from_content_list(self):
        entry = {"content": [{"value": "  Extracted body text  "}]}
        assert _extract_content(entry) == "Extracted body text"

    def test_extract_content_from_content_encoded(self):
        entry = {"content_encoded": "  Encoded HTML/prose text  "}
        assert _extract_content(entry) == "Encoded HTML/prose text"

    def test_extract_content_empty_fallback(self):
        assert _extract_content({}) is None
        assert _extract_content({"content": [{"value": "   "}]}) is None


class TestFetchFeed:
    def test_fetch_feed_success(self):
        async def run():
            xml_feed = """<?xml version="1.0" encoding="UTF-8"?>
            <rss version="2.0">
                <channel>
                    <title>Test Feed</title>
                    <link>https://example.com</link>
                    <item>
                        <title>Article 1</title>
                        <link>https://example.com/article1</link>
                        <description>Summary 1</description>
                    </item>
                    <item>
                        <title>Article 2</title>
                        <link>https://example.com/article2</link>
                        <description>Summary 2</description>
                    </item>
                    <item>
                        <title></title>
                        <link>https://example.com/invalid</link>
                    </item>
                </channel>
            </rss>"""
            mock_resp = MagicMock()
            mock_resp.text = xml_feed
            mock_resp.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__.return_value = mock_client
                articles = await fetch_feed("https://example.com/rss")

                assert len(articles) == 2
                assert articles[0].title == "Article 1"
                assert articles[0].url == "https://example.com/article1"
                assert articles[0].description == "Summary 1"
                assert articles[1].title == "Article 2"

        asyncio.run(run())

    def test_fetch_feed_resolves_relative_links_against_final_url(self):
        async def run():
            xml_feed = """<?xml version="1.0" encoding="UTF-8"?>
            <rss version="2.0">
                <channel>
                    <title>Relative Feed</title>
                    <item>
                        <title>Relative story</title>
                        <link>/world/story</link>
                    </item>
                </channel>
            </rss>"""
            mock_resp = MagicMock()
            mock_resp.text = xml_feed
            mock_resp.url = httpx.URL("https://example.com/news/rss")
            mock_resp.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__.return_value = mock_client
                articles = await fetch_feed("https://example.com/news/rss")

            assert articles[0].url == "https://example.com/world/story"

        asyncio.run(run())

    def test_fetch_feed_propagates_timeout(self):
        async def run():
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__.return_value = mock_client
                with pytest.raises(httpx.TimeoutException):
                    await fetch_feed("https://timeout.com/rss")

        asyncio.run(run())

    def test_fetch_feed_propagates_http_error(self):
        async def run():
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "404 Not Found", request=MagicMock(), response=MagicMock()
                )
            )

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__.return_value = mock_client
                with pytest.raises(httpx.HTTPStatusError):
                    await fetch_feed("https://error.com/rss")

        asyncio.run(run())

    def test_rss_fetcher_missing_feed_url(self):
        async def run():
            source = DueSource(
                id=uuid.uuid4(),
                slug="test-missing",
                name="Test Missing",
                source_type=SourceType.RSS,
                credibility=CredibilityTier.TIER_2,
                feed_url=None,
            )
            fetcher = RSSFetcher()
            articles = await fetcher.fetch_articles(source)
            assert articles == []

        asyncio.run(run())

    def test_rss_fetcher_delegates_to_fetch_feed(self):
        async def run():
            source = DueSource(
                id=uuid.uuid4(),
                slug="test-rss",
                name="Test RSS",
                source_type=SourceType.RSS,
                credibility=CredibilityTier.TIER_2,
                feed_url="https://example.com/feed.xml",
            )
            fetcher = RSSFetcher()
            expected = [
                ParsedArticle(
                    title="Headline",
                    url="https://example.com/1",
                    description="Desc",
                )
            ]
            with patch(
                "hermes_worker.services.fetchers.rss.fetch_feed",
                AsyncMock(return_value=expected),
            ) as mock_fetch:
                result = await fetcher.fetch_articles(source)
                assert result == expected
                mock_fetch.assert_awaited_once_with(
                    "https://example.com/feed.xml",
                    user_agent="HermesGeospatialNews/1.0",
                )

        asyncio.run(run())

    def test_parse_date_uses_updated_when_published_missing(self):
        time_tuple = time.strptime("2026-10-03 12:00:00", "%Y-%m-%d %H:%M:%S")
        parsed = _parse_date({"updated_parsed": time_tuple})
        assert parsed == datetime(2026, 10, 3, 12, 0, 0, tzinfo=UTC)

    def test_rss_fetcher_falls_back_when_primary_is_empty(self):
        async def run():
            source = DueSource(
                id=uuid.uuid4(),
                slug="test-fallback",
                name="Test Fallback",
                source_type=SourceType.RSS,
                credibility=CredibilityTier.TIER_2,
                feed_url="https://example.com/primary.xml",
                fallback_feed_url="https://fallback.example.com/feed.xml",
            )
            expected = [
                ParsedArticle(
                    title="Fallback headline",
                    url="https://fallback.example.com/1",
                    description="Desc",
                )
            ]

            async def fake_fetch(url: str, *, user_agent: str):
                assert user_agent == "HermesGeospatialNews/1.0"
                return [] if url.endswith("primary.xml") else expected

            with patch(
                "hermes_worker.services.fetchers.rss.fetch_feed",
                side_effect=fake_fetch,
            ) as mock_fetch:
                result = await RSSFetcher().fetch_articles(source)

            assert result == expected
            assert mock_fetch.await_count == 2

        asyncio.run(run())

    def test_rss_fetcher_falls_back_after_primary_error(self):
        async def run():
            source = DueSource(
                id=uuid.uuid4(),
                slug="test-fallback-error",
                name="Test Fallback Error",
                source_type=SourceType.RSS,
                credibility=CredibilityTier.TIER_2,
                feed_url="https://example.com/primary.xml",
                fallback_feed_url="https://fallback.example.com/feed.xml",
            )
            expected = [
                ParsedArticle(
                    title="Fallback headline",
                    url="https://fallback.example.com/1",
                    description="Desc",
                )
            ]

            async def fake_fetch(url: str, *, user_agent: str):
                if url.endswith("primary.xml"):
                    raise httpx.ConnectError("unreachable")
                return expected

            with patch(
                "hermes_worker.services.fetchers.rss.fetch_feed",
                side_effect=fake_fetch,
            ):
                result = await RSSFetcher().fetch_articles(source)

            assert result == expected

        asyncio.run(run())

    def test_rss_fetcher_raises_when_all_feeds_fail(self):
        async def run():
            source = DueSource(
                id=uuid.uuid4(),
                slug="test-all-fail",
                name="Test All Fail",
                source_type=SourceType.RSS,
                credibility=CredibilityTier.TIER_2,
                feed_url="https://example.com/primary.xml",
                fallback_feed_url="https://fallback.example.com/feed.xml",
            )

            with (
                patch(
                    "hermes_worker.services.fetchers.rss.fetch_feed",
                    new_callable=AsyncMock,
                    side_effect=httpx.ConnectError("unreachable"),
                ),
                pytest.raises(httpx.ConnectError),
            ):
                await RSSFetcher().fetch_articles(source)

        asyncio.run(run())

    def test_fetch_feed_strips_html_from_summary_and_content(self):
        rss_xml = """<?xml version="1.0" encoding="UTF-8" ?>
        <rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
          <channel>
            <title>Test Feed</title>
            <item>
              <title>Nvidia CEO returns</title>
              <link>https://news.google.com/rss/articles/CBMi123?oc=5</link>
              <description>&lt;a href="https://news.google.com/rss/articles/CBMi123"&gt;Nvidia CEO returns&lt;/a&gt;&amp;nbsp;&lt;font color="#6f6f6f"&gt;Reuters&lt;/font&gt;</description>
              <content:encoded>&lt;p&gt;Nvidia chief &lt;b&gt;Jensen Huang&lt;/b&gt; resumed Silicon Valley operations Tuesday.&lt;/p&gt;</content:encoded>
            </item>
          </channel>
        </rss>"""

        async def run():
            mock_resp = MagicMock()
            mock_resp.text = rss_xml
            mock_resp.url = "https://news.google.com/rss/search"
            mock_resp.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
                articles = await fetch_feed("https://news.google.com/rss/search")

            assert len(articles) == 1
            assert articles[0].description == "Nvidia CEO returns Reuters"
            assert (
                articles[0].content
                == "Nvidia chief Jensen Huang resumed Silicon Valley operations Tuesday."
            )

        asyncio.run(run())
