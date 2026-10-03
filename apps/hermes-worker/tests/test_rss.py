"""Unit tests for hermes_worker.services.rss feed parsing and article extraction."""

import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from hermes_worker.services.rss import (
    ParsedArticle,
    _extract_content,
    _parse_date,
    _truncate_to_words,
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
        # 500 words plus "..."
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
        # time tuple: (2026, 10, 3, 12, 0, 0, 0, 0, 0)
        time_tuple = time.strptime("2026-10-03 12:00:00", "%Y-%m-%d %H:%M:%S")
        entry = {"published_parsed": time_tuple}
        parsed = _parse_date(entry)
        assert parsed == datetime(2026, 10, 3, 12, 0, 0)

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

    def test_fetch_feed_handles_timeout(self):
        async def run():
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__.return_value = mock_client
                articles = await fetch_feed("https://timeout.com/rss")
                assert articles == []

        asyncio.run(run())

    def test_fetch_feed_handles_http_error(self):
        async def run():
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.HTTPStatusError("404 Not Found", request=MagicMock(), response=MagicMock()))

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__.return_value = mock_client
                articles = await fetch_feed("https://error.com/rss")
                assert articles == []

        asyncio.run(run())
