"""Tests for hermes-api AiService timeline extraction and context triage."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from hermes_api.services.ai_service import (
    AiService,
    TimelineSearchQuery,
    TlEdgeExtraction,
    TlExtractionResponse,
    tlNodeExtraction,
)


@pytest.fixture
def ai_service(monkeypatch):
    monkeypatch.setenv("LLM_API", "fake-llm-key")
    monkeypatch.setenv("LLM_MODEL", "mistral/ministral-8b-latest")
    monkeypatch.setenv("LLM_API_1", "fake-fallback-key")
    monkeypatch.setenv("LLM_MODEL_1", "nvidia_nim/meta/llama-3.1-70b-instruct")
    return AiService()


class TestExtractTl:
    def test_returns_none_for_empty_prose(self, ai_service: AiService) -> None:
        result = asyncio.run(ai_service.extract_tl("Title", "   "))
        assert result is None

    @patch("litellm.Router.acompletion")
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

    @patch("litellm.Router.acompletion")
    def test_extract_tl_handles_localized_dict_summary(
        self, mock_acompletion: AsyncMock, ai_service: AiService
    ) -> None:
        raw_json = (
            '{"tl_summary": {"en": "The assassination shaping its trajectory."}, '
            '"nodes": [{"date": "2021-07-07", "headline": {"en": "President assassinated"}, '
            '"location_name": {"en": "Port-au-Prince, Haiti"}, "summary": {"en": "Moise was killed."}}], '
            '"edges": []}'
        )
        mock_res = MagicMock()
        mock_res.choices = [MagicMock(message=MagicMock(content=raw_json))]
        mock_acompletion.return_value = mock_res

        result = asyncio.run(
            ai_service.extract_tl("Assassination of Jovenel Moïse", "Prose text")
        )

        assert result is not None
        assert result.tl_summary == "The assassination shaping its trajectory."
        assert len(result.nodes) == 1
        assert result.nodes[0].headline == "President assassinated"
        assert result.nodes[0].location_name == "Port-au-Prince, Haiti"
        assert result.nodes[0].summary == "Moise was killed."


class TestAnalyzeTlContext:
    @patch("litellm.Router.acompletion")
    def test_successful_context_analysis(
        self, mock_acompletion: AsyncMock, ai_service: AiService
    ) -> None:
        response_json = TimelineSearchQuery(
            is_tl_worthy=True,
            wiki_search_query="2022 Russian invasion of Ukraine",
        ).model_dump_json()

        mock_res = MagicMock()
        mock_res.choices = [MagicMock(message=MagicMock(content=response_json))]
        mock_acompletion.return_value = mock_res

        result = asyncio.run(
            ai_service.analyze_tl_context("Missile strike reported near Kyiv")
        )

        assert result is not None
        assert result.is_tl_worthy is True
        assert result.wiki_search_query == "2022 Russian invasion of Ukraine"

    @patch("litellm.Router.acompletion")
    def test_handles_llm_failure(
        self, mock_acompletion: AsyncMock, ai_service: AiService
    ) -> None:
        mock_acompletion.side_effect = Exception("Router timeout")
        result = asyncio.run(
            ai_service.analyze_tl_context("Some routine news headline")
        )
        assert result is None


class TestRouterFallback:
    def test_router_configuration(self, ai_service: AiService) -> None:
        assert len(ai_service.router.model_list) == 2
        assert ai_service.router.model_list[0]["model_name"] == "primary-extractor"
        assert ai_service.router.model_list[1]["model_name"] == "fallback-extractor"
        assert ai_service.router.fallbacks == [
            {"primary-extractor": ["fallback-extractor"]}
        ]
