"""Unit tests for HermesAiClient and domain extractors."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hermes_ai.client import HermesAiClient
from hermes_ai.core.config import AiConfig
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
        primary_model="mistral/ministral-8b-latest",
        primary_api_key="primary-key",
        fallback_model="nvidia_nim/mistral-nemotron",
        fallback_api_key="fallback-key",
        embed_model="nvidia/nemotron-3-embed-1b",
        embed_api_key="embed-key",
    )


def test_init_raises_without_primary_credentials() -> None:
    with pytest.raises(
        ValueError, match="primary_api_key and primary_model are required"
    ):
        HermesAiClient(AiConfig(primary_model="", primary_api_key=""))


def test_init_succeeds_with_primary_only() -> None:
    client = HermesAiClient(
        AiConfig(primary_model="mistral/mistral-large", primary_api_key="key")
    )
    assert client.router is not None


@patch("litellm.Router.acompletion")
def test_call_llm_success(mock_acompletion: AsyncMock, base_config: AiConfig) -> None:
    client = HermesAiClient(base_config)
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
        client.call_llm(
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
    client = HermesAiClient(base_config)
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
    results = asyncio.run(client.extract_events(articles))

    assert len(results) == 1
    assert results[0] is not None
    assert results[0].headline == "Berlin Tech Summit"
    assert results[0].category_color == "#06B6D4"


@patch("litellm.Router.acompletion")
def test_extract_tl_success(mock_acompletion: AsyncMock, base_config: AiConfig) -> None:
    client = HermesAiClient(base_config)
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

    res = asyncio.run(client.extract_tl("Page Title", "Prose body"))
    assert res is not None
    assert res.tl_summary == "Historical arc"
    assert len(res.nodes) == 1


@patch("litellm.aembedding")
def test_gen_embeddings_success(
    mock_aembedding: AsyncMock, base_config: AiConfig
) -> None:
    client = HermesAiClient(base_config)
    mock_res = MagicMock()
    mock_res.data = [{"embedding": [0.1, 0.2, 0.3]}]
    mock_aembedding.return_value = mock_res

    embeddings = asyncio.run(client.gen_embeddings(["Sample text"]))
    assert len(embeddings) == 1
    assert embeddings[0] == [0.1, 0.2, 0.3]


def test_gen_embeddings_empty_list(base_config: AiConfig) -> None:
    client = HermesAiClient(base_config)
    assert asyncio.run(client.gen_embeddings([])) == []
