"""Unit tests for hermes_worker.services.ai event extraction, geoparsing, and fallback logic."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from hermes_ai.models.events import (
    ArticleInput,
    ExtractedEvent,
)
from hermes_ai.utils.coercion import coerce_to_str
from hermes_worker.services.ai import AiService


class TestAiHelpers:
    def test_coerce_to_str_with_string(self):
        assert coerce_to_str("simple text") == "simple text"

    def test_coerce_to_str_with_dict(self):
        assert coerce_to_str({"en": "English text"}) == "English text"
        assert coerce_to_str({"summary": "Summary text"}) == "Summary text"
        assert coerce_to_str({"other": "Fallback text"}) == "Fallback text"

    def test_coerce_to_str_with_list(self):
        assert coerce_to_str(["part1", "part2"]) == "part1 part2"
        assert coerce_to_str(["part1", None, "   ", "part2"]) == "part1 part2"

    def test_coerce_to_str_with_none(self):
        assert coerce_to_str(None) == ""

    def test_coerce_to_str_with_empty_or_non_string_dict(self):
        assert coerce_to_str({}) == ""
        assert coerce_to_str({"count": 42}) == ""
        assert coerce_to_str({"en": "  "}) == ""

    def test_coerce_to_str_with_bool(self):
        assert coerce_to_str(False) == ""
        assert coerce_to_str(True) == ""

    def test_coerce_to_str_with_scalar(self):
        assert coerce_to_str(42) == "42"


class TestExtractedEventModel:
    def test_valid_extracted_event(self):
        event = ExtractedEvent(
            article_index=0,
            has_location=True,
            location_name="Nairobi, Kenya",
            country_code="KE",
            headline="Nairobi Trade Summit Begins",
            summary="Delegates gathered in Nairobi to discuss economic partnerships.",
            category="ECONOMY",
            matched_event_id=None,
        )
        assert event.article_index == 0
        assert event.has_location is True
        assert event.location_name == "Nairobi, Kenya"
        assert event.country_code == "KE"
        assert event.category == "ECONOMY"


class TestWorkerAiService:
    @pytest.fixture(autouse=True)
    def mock_ai_settings(self, monkeypatch):
        monkeypatch.setattr(
            "hermes_worker.services.ai.settings.LLM_API", "mock-llm-key"
        )
        monkeypatch.setattr(
            "hermes_worker.services.ai.settings.LLM_MODEL", "mistral/mistral-large"
        )
        monkeypatch.setattr(
            "hermes_worker.services.ai.settings.EMBED_API", "mock-embed-key"
        )
        monkeypatch.setattr(
            "hermes_worker.services.ai.settings.EMBED_MODEL",
            "nvidia/nemotron-3-embed-1b",
        )

    def test_get_metadata_empty_input(self):
        async def run():
            svc = AiService()
            res = await svc.get_metadata(articles=[], existing_events=[])
            assert res == []

        asyncio.run(run())

    def test_get_metadata_successful_extraction(self):
        async def run():
            svc = AiService()
            articles = [
                ArticleInput(
                    title="Global Oil Prices Rise",
                    content="Oil markets surged today amid supply concerns.",
                )
            ]

            mock_event = ExtractedEvent(
                article_index=0,
                has_location=False,
                location_name=None,
                country_code=None,
                headline="Global Oil Prices Rise Amid Supply Concerns",
                summary="Crude oil benchmarks gained significantly following inventory reports.",
                category="ECONOMY",
                matched_event_id=None,
            )

            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content=f'{{"events": [{mock_event.model_dump_json()}]}}'
                    )
                )
            ]

            with patch.object(
                svc._router, "acompletion", new_callable=AsyncMock
            ) as mock_complete:
                mock_complete.return_value = mock_response
                results = await svc.get_metadata(articles=articles, existing_events=[])

                assert len(results) == 1
                assert results[0] is not None
                assert (
                    results[0].headline == "Global Oil Prices Rise Amid Supply Concerns"
                )
                assert results[0].category == "ECONOMY"

        asyncio.run(run())

    def test_get_metadata_handles_api_failure(self):
        async def run():
            svc = AiService()
            articles = [ArticleInput(title="Test Article", content="Test content")]

            with patch.object(
                svc._router, "acompletion", new_callable=AsyncMock
            ) as mock_complete:
                mock_complete.side_effect = Exception("LLM connection timeout")
                results = await svc.get_metadata(articles=articles, existing_events=[])
                # Should return [None] corresponding to the input article on failure
                assert results == [None]

        asyncio.run(run())

    def test_gen_embeddings_empty_input(self):
        async def run():
            svc = AiService()
            res = await svc.gen_embeddings([])
            assert res == []

        asyncio.run(run())
