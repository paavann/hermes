"""Unit tests for hermes_worker.core.ai client construction and extraction wiring."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from hermes_ai.client import HermesAi
from hermes_ai.models.events import ArticleInput, ExtractedEvent
from hermes_ai.utils.coercion import coerce_to_str
from hermes_worker.core.ai import create_ai_client
from hermes_worker.core.config import Settings


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "DB_PASSWORD": "worker-secret-pass",
        "LLM_API": "mock-llm-key",
        "LLM_MODEL": "mistral/mistral-large",
        "EMBED_API": "mock-embed-key",
        "EMBED_MODEL": "nvidia_nim/nvidia/nemotron-3-embed-1b",
        "LANGFUSE_PUBLIC_KEY": "",
        "LANGFUSE_SECRET_KEY": "",
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


class TestAiHelpers:
    def test_coerce_to_str_with_string(self) -> None:
        assert coerce_to_str("simple text") == "simple text"

    def test_coerce_to_str_with_dict(self) -> None:
        assert coerce_to_str({"en": "English text"}) == "English text"
        assert coerce_to_str({"summary": "Summary text"}) == "Summary text"
        assert coerce_to_str({"other": "Fallback text"}) == "Fallback text"

    def test_coerce_to_str_with_list(self) -> None:
        assert coerce_to_str(["part1", "part2"]) == "part1 part2"
        assert coerce_to_str(["part1", None, "   ", "part2"]) == "part1 part2"

    def test_coerce_to_str_with_none(self) -> None:
        assert coerce_to_str(None) == ""

    def test_coerce_to_str_with_empty_or_non_string_dict(self) -> None:
        assert coerce_to_str({}) == ""
        assert coerce_to_str({"count": 42}) == ""
        assert coerce_to_str({"en": "  "}) == ""

    def test_coerce_to_str_with_bool(self) -> None:
        assert coerce_to_str(False) == ""
        assert coerce_to_str(True) == ""

    def test_coerce_to_str_with_scalar(self) -> None:
        assert coerce_to_str(42) == "42"


class TestExtractedEventModel:
    def test_valid_extracted_event(self) -> None:
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
        assert event.impact_level == "MODERATE"

    def test_coerces_model_output_shapes(self) -> None:
        event = ExtractedEvent.model_validate(
            {
                "article_index": 1,
                "has_location": "true",
                "location_name": {"en": "Geneva, Switzerland"},
                "headline": {"en": "Ceasefire talks resume"},
                "summary": ["Delegations", "met on Tuesday."],
                "category": "politics",
                "impact_level": "major",
            }
        )

        assert event.has_location is True
        assert event.location_name == "Geneva, Switzerland"
        assert event.headline == "Ceasefire talks resume"
        assert event.summary == "Delegations met on Tuesday."
        assert event.impact_level == "MAJOR"

    def test_unknown_impact_level_falls_back_to_moderate(self) -> None:
        event = ExtractedEvent(
            article_index=0,
            has_location=False,
            headline="Headline",
            summary="Summary.",
            category="TECHNOLOGY",
            impact_level="CATASTROPHIC",
        )
        assert event.impact_level == "MODERATE"


class TestWorkerAiClientFactory:
    def test_create_ai_client_success(self) -> None:
        client = create_ai_client(_settings())

        assert isinstance(client, HermesAi)
        assert client.config.routes["extractor"].primary.model == "mistral/mistral-large"
        assert client.config.routes["extractor"].primary.api_key == "mock-llm-key"
        assert client.config.routes["extractor"].primary.rpm == 26
        assert client.config.routes["embed"].primary.model == (
            "nvidia_nim/nvidia/nemotron-3-embed-1b"
        )
        assert client.config.routes["embed"].primary.rpm == 90
        assert client.config.tracing_enabled is False

    def test_create_ai_client_builds_fallback_chain(self) -> None:
        client = create_ai_client(
            _settings(
                LLM_MODEL_1="mistral/ministral-8b-latest",
                LLM_API_1="fallback-llm-key",
                EMBED_MODEL_1="nvidia_nim/nvidia/nemotron-embed-fallback",
                EMBED_API_1="fallback-embed-key",
            )
        )

        extractor_fallbacks = client.config.routes["extractor"].fallbacks
        embed_fallbacks = client.config.routes["embed"].fallbacks
        assert len(extractor_fallbacks) == 1
        assert extractor_fallbacks[0].model == "mistral/ministral-8b-latest"
        assert extractor_fallbacks[0].api_key == "fallback-llm-key"
        assert len(embed_fallbacks) == 1
        assert embed_fallbacks[0].api_key == "fallback-embed-key"

    def test_omits_route_when_credentials_are_missing(self) -> None:
        client = create_ai_client(
            _settings(
                LLM_API="",
                LLM_MODEL="",
                EMBED_MODEL_1="mistral/fallback",
                EMBED_API_1="",
            )
        )

        assert "extractor" not in client.config.routes
        assert "embed" in client.config.routes

    def test_tracing_requires_both_langfuse_keys(self) -> None:
        partial = create_ai_client(_settings(LANGFUSE_PUBLIC_KEY="public-only"))
        assert partial.config.tracing_enabled is False

        traced = create_ai_client(
            _settings(
                LANGFUSE_PUBLIC_KEY="public-key",
                LANGFUSE_SECRET_KEY="secret-key",
            )
        )
        assert traced.config.tracing_enabled is True
        assert traced.config.tracing_tags == ["hermes-worker", "development"]
        assert traced.config.langfuse_public_key == "public-key"
        assert traced.config.langfuse_secret_key == "secret-key"

    def test_extract_events_empty_input(self) -> None:
        async def run() -> None:
            client = create_ai_client(_settings())
            res = await client.events.extract(articles=[], existing_events=[])
            assert res == []

        asyncio.run(run())

    def test_extract_events_successful_extraction(self) -> None:
        async def run() -> None:
            client = create_ai_client(_settings())
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

            with patch(
                "litellm.Router.acompletion", new_callable=AsyncMock
            ) as mock_complete:
                mock_complete.return_value = mock_response
                results = await client.events.extract(
                    articles=articles, existing_events=[]
                )

                assert len(results) == 1
                assert results[0] is not None
                assert (
                    results[0].headline == "Global Oil Prices Rise Amid Supply Concerns"
                )
                assert results[0].category == "ECONOMY"
                assert results[0].category_color == "#22C55E"

        asyncio.run(run())

    def test_extract_events_handles_api_failure(self) -> None:
        async def run() -> None:
            client = create_ai_client(_settings())
            articles = [ArticleInput(title="Test Article", content="Test content")]

            with patch(
                "litellm.Router.acompletion", new_callable=AsyncMock
            ) as mock_complete:
                mock_complete.side_effect = Exception("LLM connection timeout")
                results = await client.events.extract(
                    articles=articles, existing_events=[]
                )
                assert results == [None]

        asyncio.run(run())

    def test_extract_events_reindexes_out_of_order_results(self) -> None:
        async def run() -> None:
            client = create_ai_client(_settings())
            articles = [
                ArticleInput(title="First", content="First content."),
                ArticleInput(title="Second", content="Second content."),
            ]

            second = ExtractedEvent(
                article_index=1,
                has_location=False,
                headline="Second result",
                summary="Second summary.",
                category="POLITICS",
            )
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content=f'{{"events": [{second.model_dump_json()}]}}'
                    )
                )
            ]

            with patch(
                "litellm.Router.acompletion", new_callable=AsyncMock
            ) as mock_complete:
                mock_complete.return_value = mock_response
                results = await client.events.extract(
                    articles=articles, existing_events=[]
                )

                assert results[0] is None
                assert results[1] is not None
                assert results[1].headline == "Second result"

        asyncio.run(run())

    def test_gen_embeddings_empty_input(self) -> None:
        async def run() -> None:
            client = create_ai_client(_settings())
            res = await client.llm.gen_embeddings([])
            assert res == []

        asyncio.run(run())

    def test_gen_embeddings_without_route_degrades_to_none(self) -> None:
        async def run() -> None:
            client = create_ai_client(_settings(EMBED_API="", EMBED_MODEL=""))
            res = await client.llm.gen_embeddings(["alpha", "beta"])
            assert res == [None, None]

        asyncio.run(run())


@pytest.mark.parametrize(
    ("value", "expected"),
    [("true", True), ("1", True), ("yes", True), ("false", False), (0, False)],
)
def test_has_location_coercion(value: object, expected: bool) -> None:
    event = ExtractedEvent.model_validate(
        {
            "article_index": 0,
            "has_location": value,
            "headline": "Headline",
            "summary": "Summary.",
            "category": "ECONOMY",
        }
    )
    assert event.has_location is expected
