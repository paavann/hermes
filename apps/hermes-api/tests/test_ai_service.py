"""Tests for AiService extraction and embeddings."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hermes_api.services.ai_service import (
    AiService,
    ArticleInput,
    ExtractedEvent,
    ExtractionResponse,
    TlEdgeExtraction,
    TlExtractionResponse,
    tlNodeExtraction,
)


@pytest.fixture
def ai_service(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "fake-llm-key")
    monkeypatch.setenv("EMBED_API_KEY", "fake-embed-key")
    monkeypatch.setenv("LLM_MODEL", "gemini/gemini-2.5-flash")
    monkeypatch.setenv("EMBED_MODEL", "gemini/text-embedding-004")
    return AiService()


class TestGetMetadata:
    def test_returns_empty_for_no_articles(self, ai_service: AiService) -> None:
        result = asyncio.run(ai_service.get_metadata([], []))
        assert result == []

    @patch("litellm.acompletion")
    def test_successful_batch_extraction(
        self, mock_acompletion: AsyncMock, ai_service: AiService
    ) -> None:
        articles = [
            ArticleInput(title="Article 0", content="Content 0"),
            ArticleInput(title="Article 1", content="Content 1"),
        ]

        response_json = ExtractionResponse(
            events=[
                ExtractedEvent(
                    article_index=1,
                    has_location=True,
                    location_name="London, UK",
                    country_code="GB",
                    headline="Headline 1",
                    summary="Summary 1",
                    category="POLITICS",
                ),
                ExtractedEvent(
                    article_index=0,
                    has_location=True,
                    location_name="Ankara, Turkey",
                    country_code="TR",
                    headline="Headline 0",
                    summary="Summary 0",
                    category="NATURAL_DISASTER",
                ),
            ]
        ).model_dump_json()

        mock_res = MagicMock()
        mock_res.choices = [MagicMock(message=MagicMock(content=response_json))]
        mock_acompletion.return_value = mock_res

        results = asyncio.run(ai_service.get_metadata(articles, []))

        assert len(results) == 2
        assert results[0] is not None
        assert results[0].headline == "Headline 0"
        assert results[1] is not None
        assert results[1].headline == "Headline 1"

    @patch("litellm.acompletion")
    def test_handles_api_failure(
        self, mock_acompletion: AsyncMock, ai_service: AiService
    ) -> None:
        articles = [ArticleInput(title="Article 0", content="Content 0")]
        mock_acompletion.side_effect = Exception("LLM Error")

        results = asyncio.run(ai_service.get_metadata(articles, []))
        assert results == [None]


class TestExtractTl:
    def test_returns_none_for_empty_prose(self, ai_service: AiService) -> None:
        result = asyncio.run(ai_service.extract_tl("Title", "   "))
        assert result is None

    @patch("litellm.acompletion")
    def test_successful_tl_extraction(
        self, mock_acompletion: AsyncMock, ai_service: AiService
    ) -> None:
        response_json = TlExtractionResponse(
            tl_summary="Overarching historical arc.",
            nodes=[
                tlNodeExtraction(
                    date="2023-10-06",
                    headline="Event 0",
                    location_name="Location 0",
                    summary="Summary 0",
                ),
                tlNodeExtraction(
                    date="2023-10-07",
                    headline="Event 1",
                    location_name="Location 1",
                    summary="Summary 1",
                ),
            ],
            edges=[
                TlEdgeExtraction(
                    source_index=0,
                    target_index=1,
                    relationship="triggered",
                )
            ],
        ).model_dump_json()

        mock_res = MagicMock()
        mock_res.choices = [MagicMock(message=MagicMock(content=response_json))]
        mock_acompletion.return_value = mock_res

        result = asyncio.run(ai_service.extract_tl("Timeline of X", "Prose text"))

        assert result is not None
        assert result.tl_summary == "Overarching historical arc."
        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        assert result.edges[0].relationship == "triggered"
