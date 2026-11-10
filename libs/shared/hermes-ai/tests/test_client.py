"""Unit tests for HermesAi and domain extractors."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hermes_ai.client import HermesAi
from hermes_ai.core.config import AiConfig, ModelRoute, ModelTarget
from hermes_ai.exceptions import ConfigurationError, SchemaValidationError
from hermes_ai.models.events import ArticleInput, ExtractedEvent
from hermes_ai.models.tl import (
    TlEdgeExtraction,
    TlExtractionResponse,
    TlNodeExtraction,
    TlSearchQuery,
)


@pytest.fixture
def base_config() -> AiConfig:
    return AiConfig(
        routes={
            "extractor": ModelRoute(
                primary=ModelTarget(
                    model="mistral/ministral-8b-latest", api_key="primary-key"
                ),
                fallbacks=(
                    ModelTarget(
                        model="nvidia_nim/meta/llama-3.1-70b-instruct",
                        api_key="fallback-key",
                    ),
                ),
            ),
            "embed": ModelRoute(
                primary=ModelTarget(
                    model="nvidia_nim/nvidia/nemotron-3-embed-1b",
                    api_key="embed-key",
                ),
            ),
        },
    )


def test_init_raises_without_primary_credentials() -> None:
    with pytest.raises(
        ConfigurationError,
        match="extractor primary model and api key are required",
    ):
        HermesAi(
            AiConfig(
                routes={
                    "extractor": ModelRoute(primary=ModelTarget(model="", api_key=""))
                }
            )
        )


def test_init_succeeds_with_primary_only() -> None:
    client = HermesAi(
        AiConfig(
            routes={
                "extractor": ModelRoute(
                    primary=ModelTarget(model="mistral/mistral-large", api_key="key")
                )
            }
        )
    )
    assert client.config.routes["extractor"].primary.model == "mistral/mistral-large"
    assert len(client.config.routes["extractor"].fallbacks) == 0


@patch("litellm.Router.acompletion")
def test_call_llm_success(mock_acompletion: AsyncMock, base_config: AiConfig) -> None:
    client = HermesAi(base_config)
    mock_res = MagicMock()
    mock_res.choices = [
        MagicMock(
            message=MagicMock(
                content='{"is_tl_worthy": true, "wiki_search_query": "Treaty"}'
            )
        )
    ]
    mock_acompletion.return_value = mock_res

    res = asyncio.run(
        client.llm.call_llm(
            sys_prompt="system",
            user_prompt="user",
            res_model=TlSearchQuery,
            schema_name="triage",
        )
    )
    assert res is not None
    assert res.is_tl_worthy is True
    assert res.wiki_search_query == "Treaty"


@patch("litellm.Router.acompletion")
def test_extract_events_success(
    mock_acompletion: AsyncMock, base_config: AiConfig
) -> None:
    client = HermesAi(base_config)
    event = ExtractedEvent(
        article_index=0,
        has_location=True,
        location_name="Berlin, Germany",
        country_code="DE",
        headline="Berlin Tech Summit",
        summary="Summit held in Berlin.",
        category="TECHNOLOGY",
    )
    mock_res = MagicMock()
    mock_res.choices = [
        MagicMock(
            message=MagicMock(content=f'{{"events": [{event.model_dump_json()}]}}')
        )
    ]
    mock_acompletion.return_value = mock_res

    articles = [ArticleInput(title="Berlin Tech Summit", content="Full text")]
    results = asyncio.run(client.events.extract(articles))

    assert len(results) == 1
    assert results[0] is not None
    assert results[0].headline == "Berlin Tech Summit"
    assert results[0].category_color == "#06B6D4"


@patch("litellm.Router.acompletion")
def test_extract_tl_success(mock_acompletion: AsyncMock, base_config: AiConfig) -> None:
    client = HermesAi(base_config)
    tl = TlExtractionResponse(
        tl_summary="Historical arc",
        nodes=[
            TlNodeExtraction(
                date="2020-01-01",
                headline="Inception",
                summary="Started here",
            )
        ],
        edges=[
            TlEdgeExtraction(
                source_index=0,
                target_index=0,
                relationship="self",
            )
        ],
    )
    mock_res = MagicMock()
    mock_res.choices = [MagicMock(message=MagicMock(content=tl.model_dump_json()))]
    mock_acompletion.return_value = mock_res

    res = asyncio.run(client.timelines.extract("Page Title", "Prose body"))
    assert res is not None
    assert res.tl_summary == "Historical arc"
    assert len(res.nodes) == 1


@patch("litellm.aembedding")
def test_gen_embeddings_success(
    mock_aembedding: AsyncMock, base_config: AiConfig
) -> None:
    client = HermesAi(base_config)
    mock_res = MagicMock()
    mock_res.data = [{"embedding": [0.1, 0.2, 0.3]}]
    mock_aembedding.return_value = mock_res

    embeddings = asyncio.run(client.llm.gen_embeddings(["Sample text"]))
    assert len(embeddings) == 1
    assert embeddings[0] == [0.1, 0.2, 0.3]


def test_gen_embeddings_empty_list(base_config: AiConfig) -> None:
    client = HermesAi(base_config)
    assert asyncio.run(client.llm.gen_embeddings([])) == []


@patch("litellm.Router.acompletion")
def test_call_llm_raises_schema_validation_error(
    mock_acompletion: AsyncMock, base_config: AiConfig
) -> None:
    client = HermesAi(base_config)
    bad_res = MagicMock()
    bad_res.choices = [MagicMock(message=MagicMock(content='{"invalid": "data"}'))]
    mock_acompletion.return_value = bad_res

    with pytest.raises(SchemaValidationError):
        asyncio.run(
            client.llm.call_llm(
                sys_prompt="system",
                user_prompt="user",
                res_model=TlSearchQuery,
                schema_name="triage",
            )
        )


def test_async_context_manager(base_config: AiConfig) -> None:
    async def _run() -> None:
        async with HermesAi(base_config) as client:
            assert (
                client.config.routes["extractor"].primary.model
                == "mistral/ministral-8b-latest"
            )

    asyncio.run(_run())


@patch("litellm.Router.acompletion")
def test_resource_namespaces(
    mock_acompletion: AsyncMock, base_config: AiConfig
) -> None:
    client = HermesAi(base_config)
    assert client.llm is not None
    assert client.events is not None
    assert client.timelines is not None

    mock_res = MagicMock()
    mock_res.choices = [
        MagicMock(
            message=MagicMock(
                content='{"is_tl_worthy": true, "wiki_search_query": "Treaty"}'
            )
        )
    ]
    mock_acompletion.return_value = mock_res

    res = asyncio.run(client.timelines.analyze("Treaty of Versailles"))
    assert res is not None
    assert res.is_tl_worthy is True


def test_exception_hierarchy() -> None:
    from hermes_ai import (
        CircuitBreakerOpenError,
        ConfigurationError,
        GeocodingError,
        HermesAiError,
        ModelExecutionError,
        RateLimitExceededError,
        SchemaValidationError,
    )

    assert issubclass(ConfigurationError, HermesAiError)
    assert issubclass(ConfigurationError, ValueError)
    assert issubclass(ModelExecutionError, HermesAiError)
    assert issubclass(ModelExecutionError, RuntimeError)
    assert issubclass(SchemaValidationError, HermesAiError)
    assert issubclass(SchemaValidationError, ValueError)
    assert issubclass(RateLimitExceededError, HermesAiError)
    assert issubclass(RateLimitExceededError, RuntimeError)
    assert issubclass(CircuitBreakerOpenError, RateLimitExceededError)
    assert issubclass(CircuitBreakerOpenError, HermesAiError)
    assert issubclass(GeocodingError, HermesAiError)
    assert issubclass(GeocodingError, RuntimeError)
