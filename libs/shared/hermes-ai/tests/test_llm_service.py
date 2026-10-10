"""Unit tests for LlmService."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hermes_ai.core.config import AiConfig
from hermes_ai.models.events import ExtractionResponse
from hermes_ai.models.tl import TlSearchQuery
from hermes_ai.services.llm import LlmService


@pytest.fixture
def base_config() -> AiConfig:
    return AiConfig(
        primary_model="mistral/ministral-8b-latest",
        primary_api_key="primary-key",
        fallback_model="nvidia_nim/meta/llama-3.1-70b-instruct",
        fallback_api_key="fallback-key",
        embed_model="nvidia/nemotron-3-embed-1b",
        embed_api_key="embed-key",
        rpm_limit=60,
        embed_rpm_limit=120,
    )


def test_llm_service_init_raises_without_credentials() -> None:
    with pytest.raises(
        ValueError, match="primary_api_key and primary_model are required"
    ):
        LlmService(AiConfig(primary_model="", primary_api_key=""))


def test_llm_service_init_succeeds(base_config: AiConfig) -> None:
    svc = LlmService(base_config)
    assert svc.router is not None
    assert svc.rate_limiter is not None
    assert svc.embed_rate_limiter is not None


@patch("litellm.Router.acompletion")
def test_llm_service_call_llm_success(
    mock_acompletion: AsyncMock, base_config: AiConfig
) -> None:
    svc = LlmService(base_config)
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
        svc.call_llm(
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
def test_llm_service_fallback_on_validation_failure(
    mock_acompletion: AsyncMock, base_config: AiConfig
) -> None:
    svc = LlmService(base_config)
    bad_res = MagicMock()
    bad_res.choices = [MagicMock(message=MagicMock(content='{"invalid": "data"}'))]
    good_res = MagicMock()
    good_res.choices = [
        MagicMock(
            message=MagicMock(
                content='{"is_tl_worthy": true, "wiki_search_query": "Crisis"}'
            )
        )
    ]
    mock_acompletion.side_effect = [bad_res, good_res]

    res = asyncio.run(
        svc.call_llm(
            sys_prompt="system",
            user_prompt="user",
            res_model=TlSearchQuery,
            schema_name="triage",
        )
    )
    assert res is not None
    assert res.is_tl_worthy is True
    assert res.wiki_search_query == "Crisis"
    assert mock_acompletion.call_count == 2


@patch("litellm.aembedding")
def test_llm_service_gen_embeddings(
    mock_aembedding: AsyncMock, base_config: AiConfig
) -> None:
    svc = LlmService(base_config)
    mock_res = MagicMock()
    mock_res.data = [{"embedding": [0.1, 0.2, 0.3]}]
    mock_aembedding.return_value = mock_res

    embeddings = asyncio.run(svc.gen_embeddings(["sample"]))
    assert len(embeddings) == 1
    assert embeddings[0] == [0.1, 0.2, 0.3]


def test_llm_service_gen_embeddings_empty(base_config: AiConfig) -> None:
    svc = LlmService(base_config)
    assert asyncio.run(svc.gen_embeddings([])) == []


@patch("litellm.Router.acompletion")
def test_llm_service_call_llm_markdown_fence_and_raw_list(
    mock_acompletion: AsyncMock, base_config: AiConfig
) -> None:
    svc = LlmService(base_config)
    mock_res = MagicMock()
    mock_res.choices = [
        MagicMock(
            message=MagicMock(
                content="```json\n"
                '[{"article_index": 0, "has_location": false, "headline": "Fence", '
                '"summary": "Test", "category": "POLITICS"}]\n'
                "```"
            )
        )
    ]
    mock_acompletion.return_value = mock_res

    res = asyncio.run(
        svc.call_llm(
            sys_prompt="system",
            user_prompt="user",
            res_model=ExtractionResponse,
            schema_name="extraction_response",
        )
    )
    assert res is not None
    assert len(res.events) == 1
    assert res.events[0].headline == "Fence"

