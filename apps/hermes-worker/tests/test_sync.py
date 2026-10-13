"""Unit tests for hermes_worker.services.sync ingestion pipeline coordinator."""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from hermes_ai.models.events import ExtractedEvent
from hermes_db.enums import CredibilityTier
from hermes_db.services import DueSource
from hermes_worker.services.rss import ParsedArticle
from hermes_worker.services.sync import SyncService


@pytest.fixture
def dummy_due_source():
    return DueSource(
        id=uuid.uuid4(),
        name="Test News Feed",
        feed_url="https://example.com/rss",
        credibility=CredibilityTier.TIER_2,
        fetch_interval_minutes=15,
        last_fetched_at=None,
    )


class TestSyncService:
    @pytest.fixture(autouse=True)
    def mock_ai_service_class(self):
        with patch("hermes_worker.services.sync.AiService") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.gen_embeddings = AsyncMock(return_value=[[0.1] * 2048])
            mock_inst.get_metadata = AsyncMock(return_value=[])
            mock_cls.return_value = mock_inst
            yield mock_inst

    def test_sync_all_sources_no_due_sources(self):
        async def run():
            mock_session = AsyncMock()
            mock_session_ctx = MagicMock()
            mock_session_ctx.__aenter__.return_value = mock_session
            mock_session_ctx.__aexit__.return_value = None

            with (
                patch(
                    "hermes_worker.services.sync.AsyncSessionLocal",
                    return_value=mock_session_ctx,
                ),
                patch("hermes_worker.services.sync.SourceService") as mock_src_cls,
            ):
                mock_src = mock_src_cls.return_value
                mock_src.get_due_sources = AsyncMock(return_value=[])

                svc = SyncService()
                stats = await svc.sync_all_sources()

                assert stats["sources_processed"] == 0
                assert stats["articles_fetched"] == 0

        asyncio.run(run())

    def test_sync_source_empty_feed(self, dummy_due_source):
        async def run():
            with patch(
                "hermes_worker.services.sync.fetch_feed", new_callable=AsyncMock
            ) as mock_fetch:
                mock_fetch.return_value = []

                svc = SyncService()
                stats = await svc._sync_source(dummy_due_source)

                assert stats["articles_fetched"] == 0
                assert stats["articles_processed"] == 0

        asyncio.run(run())

    def test_sync_source_skips_duplicates(self, dummy_due_source):
        async def run():
            articles = [
                ParsedArticle(
                    title="A1", url="https://example.com/1", description="D1"
                ),
                ParsedArticle(
                    title="A2", url="https://example.com/2", description="D2"
                ),
            ]

            mock_session = AsyncMock()
            mock_session_ctx = MagicMock()
            mock_session_ctx.__aenter__.return_value = mock_session
            mock_session_ctx.__aexit__.return_value = None

            with (
                patch(
                    "hermes_worker.services.sync.fetch_feed", new_callable=AsyncMock
                ) as mock_fetch,
                patch(
                    "hermes_worker.services.sync.AsyncSessionLocal",
                    return_value=mock_session_ctx,
                ),
                patch("hermes_worker.services.sync.EventService") as mock_event_cls,
            ):
                mock_fetch.return_value = articles
                mock_evt = mock_event_cls.return_value
                mock_evt.article_url_exists = AsyncMock(return_value=True)

                svc = SyncService()
                stats = await svc._sync_source(dummy_due_source)

                assert stats["articles_fetched"] == 2
                assert stats["articles_skipped"] == 2
                assert stats["articles_processed"] == 0

        asyncio.run(run())

    def test_sync_source_creates_event_when_no_match(
        self, dummy_due_source, mock_ai_service_class
    ):
        async def run():
            article = ParsedArticle(
                title="New Discovery", url="https://example.com/new", description="Desc"
            )
            extraction = ExtractedEvent(
                article_index=0,
                has_location=False,
                headline="New Discovery Announced",
                summary="Scientists announced a discovery.",
                category="SCIENCE",
                matched_event_id=None,
            )

            mock_session = AsyncMock()
            mock_session_ctx = MagicMock()
            mock_session_ctx.__aenter__.return_value = mock_session
            mock_session_ctx.__aexit__.return_value = None

            with (
                patch(
                    "hermes_worker.services.sync.fetch_feed", new_callable=AsyncMock
                ) as mock_fetch,
                patch(
                    "hermes_worker.services.sync.AsyncSessionLocal",
                    return_value=mock_session_ctx,
                ),
                patch("hermes_worker.services.sync.EventService") as mock_event_cls,
            ):
                mock_fetch.return_value = [article]
                mock_evt = mock_event_cls.return_value
                mock_evt.article_url_exists = AsyncMock(return_value=False)
                mock_evt.get_active_events_by_embeddings = AsyncMock(return_value=[])
                mock_evt.create_event_with_article = AsyncMock()

                mock_ai_service_class.gen_embeddings = AsyncMock(
                    return_value=[[0.1] * 2048]
                )
                mock_ai_service_class.get_metadata = AsyncMock(
                    return_value=[extraction]
                )

                svc = SyncService()
                stats = await svc._sync_source(dummy_due_source)

                assert stats["articles_fetched"] == 1
                assert stats["events_created"] == 1
                assert stats["articles_processed"] == 1
                mock_evt.create_event_with_article.assert_awaited_once()

        asyncio.run(run())

    def test_sync_source_links_to_matched_event(
        self, dummy_due_source, mock_ai_service_class
    ):
        async def run():
            article = ParsedArticle(
                title="Second Report", url="https://example.com/sec", description="Desc"
            )
            existing_event_id = uuid.uuid4()
            extraction = ExtractedEvent(
                article_index=0,
                has_location=False,
                headline="Second Report on Event",
                summary="More details emerged.",
                category="POLITICS",
                matched_event_id=str(existing_event_id),
            )

            mock_session = AsyncMock()
            mock_session_ctx = MagicMock()
            mock_session_ctx.__aenter__.return_value = mock_session
            mock_session_ctx.__aexit__.return_value = None

            with (
                patch(
                    "hermes_worker.services.sync.fetch_feed", new_callable=AsyncMock
                ) as mock_fetch,
                patch(
                    "hermes_worker.services.sync.AsyncSessionLocal",
                    return_value=mock_session_ctx,
                ),
                patch("hermes_worker.services.sync.EventService") as mock_event_cls,
            ):
                mock_fetch.return_value = [article]
                mock_evt = mock_event_cls.return_value
                mock_evt.article_url_exists = AsyncMock(return_value=False)
                mock_evt.get_active_events_by_embeddings = AsyncMock(return_value=[])
                mock_evt.add_article_to_event = AsyncMock(return_value=True)

                mock_ai_service_class.gen_embeddings = AsyncMock(
                    return_value=[[0.1] * 2048]
                )
                mock_ai_service_class.get_metadata = AsyncMock(
                    return_value=[extraction]
                )

                svc = SyncService()
                stats = await svc._sync_source(dummy_due_source)

                assert stats["articles_fetched"] == 1
                assert stats["events_matched"] == 1
                assert stats["articles_processed"] == 1
                mock_evt.add_article_to_event.assert_awaited_once()

        asyncio.run(run())
