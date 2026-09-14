"""Tests for AiService timeline extraction."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hermes_api.services.ai_service import (
    AiService,
    ArticleInput,
    BatchTimelineExtractionResponse,
    BatchTimelinePageResult,
    TimelineEvent,
)


@pytest.fixture
def mock_genai_client():
    with patch("hermes_api.services.ai_service.genai.Client") as mock_cls:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock()
        mock_cls.return_value = mock_client
        yield mock_client


@pytest.fixture
def ai_service(mock_genai_client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    return AiService()


class TestExtractTimelineEventsBatch:
    def test_returns_empty_for_no_pages(self, ai_service: AiService) -> None:
        result = asyncio.run(ai_service.extract_timeline_events_batch([]))
        assert result == []

    def test_successful_extraction(
        self, ai_service: AiService, mock_genai_client: MagicMock
    ) -> None:
        # Arrange
        pages = [
            ArticleInput(title="Page 0", content="Content 0"),
            ArticleInput(title="Page 1", content="Content 1"),
        ]
        
        mock_response = MagicMock()
        mock_response.parsed = BatchTimelineExtractionResponse(
            results=[
                BatchTimelinePageResult(
                    page_index=1,
                    events=[
                        TimelineEvent(
                            date="2023-10-07",
                            headline="Event 1",
                            summary="Summary 1",
                            location_name="Location 1"
                        )
                    ]
                ),
                BatchTimelinePageResult(
                    page_index=0,
                    events=[
                        TimelineEvent(
                            date="2023-10-06",
                            headline="Event 0",
                            summary="Summary 0",
                            location_name="Location 0"
                        )
                    ]
                )
            ]
        )
        mock_genai_client.aio.models.generate_content.return_value = mock_response

        # Act
        result = asyncio.run(ai_service.extract_timeline_events_batch(pages))

        # Assert
        assert len(result) == 2
        # Should be ordered by input (Page 0 then Page 1)
        assert len(result[0]) == 1
        assert result[0][0].headline == "Event 0"
        
        assert len(result[1]) == 1
        assert result[1][0].headline == "Event 1"

        # Check call arguments
        mock_genai_client.aio.models.generate_content.assert_called_once()
        kwargs = mock_genai_client.aio.models.generate_content.call_args.kwargs
        assert kwargs["model"] == "gemini-2.5-flash"
        assert "Page 0" in kwargs["contents"]
        assert "Page 1" in kwargs["contents"]

    def test_handles_api_failure(
        self, ai_service: AiService, mock_genai_client: MagicMock
    ) -> None:
        pages = [ArticleInput(title="Page 0", content="Content 0")]
        mock_genai_client.aio.models.generate_content.side_effect = Exception("API error")
        
        result = asyncio.run(ai_service.extract_timeline_events_batch(pages))
        
        # Should return a list of empty lists on failure
        assert result == [[]]
