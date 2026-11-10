"""Unit tests for LlmService."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langfuse.types import MaskOtelSpansParams, OtelSpanData

from hermes_ai.core.config import AiConfig, ModelRoute, ModelTarget
from hermes_ai.exceptions import (
    ConfigurationError,
    ModelExecutionError,
    SchemaValidationError,
)
from hermes_ai.models.events import ExtractionResponse
from hermes_ai.models.tl import TlSearchQuery
from hermes_ai.services.langfuse import mask_otel_spans
from hermes_ai.services.llm import LlmService


@pytest.fixture
def base_config() -> AiConfig:
    return AiConfig(
        routes={
            "extractor": ModelRoute(
                primary=ModelTarget(
                    model="mistral/ministral-8b-latest",
                    api_key="primary-key",
                    rpm=60,
                ),
                fallbacks=(
                    ModelTarget(
                        model="nvidia_nim/meta/llama-3.1-70b-instruct",
                        api_key="fallback-key",
                        rpm=60,
                    ),
                ),
            ),
            "embed": ModelRoute(
                primary=ModelTarget(
                    model="nvidia_nim/nvidia/nemotron-3-embed-1b",
                    api_key="embed-key",
                    rpm=120,
                ),
            ),
        },
        rpm_limit=60,
    )


def test_llm_service_init_raises_without_credentials() -> None:
    with pytest.raises(
        ConfigurationError,
        match="extractor primary model and api key are required",
    ):
        LlmService(
            AiConfig(
                routes={
                    "extractor": ModelRoute(primary=ModelTarget(model="", api_key=""))
                }
            )
        )


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
def test_llm_service_raises_schema_validation_error(
    mock_acompletion: AsyncMock, base_config: AiConfig
) -> None:
    svc = LlmService(base_config)
    bad_res = MagicMock()
    bad_res.choices = [MagicMock(message=MagicMock(content='{"invalid": "data"}'))]
    mock_acompletion.return_value = bad_res

    with pytest.raises(SchemaValidationError):
        asyncio.run(
            svc.call_llm(
                sys_prompt="system",
                user_prompt="user",
                res_model=TlSearchQuery,
                schema_name="triage",
            )
        )


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


@patch("litellm.aembedding")
def test_llm_service_gen_embeddings_with_fallback(
    mock_aembedding: AsyncMock,
) -> None:
    cfg = AiConfig(
        routes={
            "extractor": ModelRoute(
                primary=ModelTarget(
                    model="mistral/ministral-8b-latest", api_key="primary-key"
                )
            ),
            "embed": ModelRoute(
                primary=ModelTarget(model="nvidia_nim/primary-embed", api_key="k1"),
                fallbacks=(
                    ModelTarget(model="nvidia_nim/fallback-embed", api_key="k2"),
                ),
            ),
        }
    )
    svc = LlmService(cfg)
    mock_res = MagicMock(data=[{"embedding": [0.5, 0.6]}])
    mock_aembedding.side_effect = [RuntimeError("Provider 500"), mock_res]

    embeddings = asyncio.run(svc.gen_embeddings(["text"]))
    assert len(embeddings) == 1
    assert embeddings[0] == [0.5, 0.6]
    assert mock_aembedding.call_count == 2


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


@patch("litellm.Router.acompletion")
def test_llm_service_call_llm_raises_model_execution_error(
    mock_acompletion: AsyncMock, base_config: AiConfig
) -> None:
    svc = LlmService(base_config)
    mock_acompletion.side_effect = RuntimeError("Provider 503 outage")

    with pytest.raises(ModelExecutionError, match="all router deployments failed"):
        asyncio.run(
            svc.call_llm(
                sys_prompt="system",
                user_prompt="user",
                res_model=TlSearchQuery,
                schema_name="triage",
            )
        )


@patch("litellm.Router.acompletion")
def test_llm_service_call_llm_raises_schema_validation_error(
    mock_acompletion: AsyncMock, base_config: AiConfig
) -> None:
    svc = LlmService(base_config)
    bad_res = MagicMock()
    bad_res.choices = [MagicMock(message=MagicMock(content='{"invalid": "data"}'))]
    mock_acompletion.side_effect = [bad_res, bad_res]

    with pytest.raises(
        SchemaValidationError,
        match="output validation failed across primary and fallback",
    ):
        asyncio.run(
            svc.call_llm(
                sys_prompt="system",
                user_prompt="user",
                res_model=TlSearchQuery,
                schema_name="triage",
            )
        )


@patch("langfuse.Langfuse")
@patch("langfuse.get_client")
def test_llm_service_tracing_enabled(
    mock_get_client: MagicMock,
    mock_langfuse: MagicMock,
    base_config: AiConfig,
) -> None:
    cfg = AiConfig(
        routes=base_config.routes,
        tracing_enabled=True,
        langfuse_public_key="pk-test",
        langfuse_secret_key="sk-test",
        langfuse_host="https://test.langfuse.com",
    )
    svc = LlmService(cfg)
    # Langfuse SDK client is now initialized via `base_url` (not the deprecated `host`).
    mock_langfuse.assert_called_once_with(
        public_key="pk-test",
        secret_key="sk-test",
        base_url="https://test.langfuse.com",
        mask_otel_spans=mask_otel_spans,
    )

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    asyncio.run(svc.aclose())
    mock_client.flush.assert_called_once()


def test_chat_and_plan_deployments_shape() -> None:
    cfg = AiConfig(
        routes={
            "extractor": ModelRoute(
                primary=ModelTarget(
                    model="mistral/ministral-8b-latest", api_key="primary-key"
                ),
            ),
            "chat": ModelRoute(
                primary=ModelTarget(
                    model="mistral/chat-model", api_key="chat-key", rpm=42
                ),
                fallbacks=(
                    ModelTarget(
                        model="nvidia_nim/chat-fallback",
                        api_key="chat-fallback-key",
                        rpm=42,
                    ),
                ),
            ),
            "plan": ModelRoute(
                primary=ModelTarget(
                    model="mistral/plan-model", api_key="plan-key", rpm=42
                ),
                fallbacks=(
                    ModelTarget(
                        model="nvidia_nim/plan-fallback",
                        api_key="plan-fallback-key",
                        rpm=42,
                    ),
                ),
            ),
        },
    )
    svc = LlmService(cfg)
    by_name = {item["model_name"]: item for item in svc.router.model_list}

    assert set(by_name) == {
        "extractor",
        "chat",
        "chat-fallback",
        "plan",
        "plan-fallback",
    }
    assert by_name["chat"]["litellm_params"]["model"] == "mistral/chat-model"
    assert by_name["chat"]["litellm_params"]["rpm"] == 42
    assert by_name["chat-fallback"]["litellm_params"]["rpm"] == 42
    assert by_name["plan"]["litellm_params"]["model"] == "mistral/plan-model"
    assert by_name["plan"]["litellm_params"]["rpm"] == 42
    assert by_name["plan-fallback"]["litellm_params"]["rpm"] == 42
    assert svc.router.fallbacks == [
        {"chat": ["chat-fallback"]},
        {"plan": ["plan-fallback"]},
    ]


def test_chat_group_without_key_raises() -> None:
    with pytest.raises(
        ConfigurationError, match="chat primary model and api key are required"
    ):
        LlmService(
            AiConfig(
                routes={
                    "extractor": ModelRoute(
                        primary=ModelTarget(
                            model="mistral/ministral-8b-latest",
                            api_key="primary-key",
                        )
                    ),
                    "chat": ModelRoute(
                        primary=ModelTarget(model="mistral/chat-model", api_key="")
                    ),
                }
            )
        )


def test_plan_group_without_key_raises() -> None:
    with pytest.raises(
        ConfigurationError, match="plan primary model and api key are required"
    ):
        LlmService(
            AiConfig(
                routes={
                    "extractor": ModelRoute(
                        primary=ModelTarget(
                            model="mistral/ministral-8b-latest",
                            api_key="primary-key",
                        )
                    ),
                    "plan": ModelRoute(
                        primary=ModelTarget(model="mistral/plan-model", api_key="")
                    ),
                }
            )
        )


@patch("litellm.Router.acompletion")
def test_llm_service_multiple_fallbacks_chain(mock_acompletion: AsyncMock) -> None:
    cfg = AiConfig(
        routes={
            "extractor": ModelRoute(
                primary=ModelTarget(model="mistral/model-primary", api_key="k0"),
                fallbacks=(
                    ModelTarget(model="nvidia_nim/model-fb-1", api_key="k1"),
                    ModelTarget(model="nvidia_nim/model-fb-2", api_key="k2"),
                ),
            )
        }
    )
    svc = LlmService(cfg)
    by_name = {item["model_name"]: item for item in svc.router.model_list}
    assert "extractor-fallback-1" in by_name
    assert "extractor-fallback-2" in by_name
    assert svc.router.fallbacks == [
        {"extractor": ["extractor-fallback-1", "extractor-fallback-2"]}
    ]

    good_res = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content='{"is_tl_worthy": true, "wiki_search_query": "Success"}'
                )
            )
        ]
    )
    mock_acompletion.return_value = good_res

    res = asyncio.run(
        svc.call_llm(
            sys_prompt="system",
            user_prompt="user",
            res_model=TlSearchQuery,
            schema_name="triage",
        )
    )
    assert res.is_tl_worthy is True
    assert res.wiki_search_query == "Success"
    mock_acompletion.assert_awaited_once_with(
        model="extractor",
        messages=[
            {"role": "system", "content": "system"},
            {"role": "user", "content": "user"},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "triage",
                "schema": TlSearchQuery.model_json_schema(),
            },
        },
    )


def test_mask_otel_spans_deletes_content_but_keeps_operational_attributes() -> None:
    span = OtelSpanData(
        trace_id="a" * 32,
        span_id="b" * 16,
        parent_span_id=None,
        name="chat",
        instrumentation_scope_name="langfuse",
        instrumentation_scope_version=None,
        attributes={
            "langfuse.observation.input": "secret",
            "langfuse.observation.output": "secret",
            "gen_ai.prompt.0.content": "secret",
            "gen_ai.completion.0.content": "secret",
            "gen_ai.input.messages": "[]",
            "gen_ai.system_instructions": "secret",
            "langfuse.observation.model.name": "mistral/chat-model",
            "langfuse.observation.start_time": "2026-01-01T00:00:00Z",
            "gen_ai.usage.input_tokens": 42,
        },
        resource_attributes={},
    )
    result = mask_otel_spans(params=MaskOtelSpansParams(spans={"span-1": span}))

    assert result is not None
    patch = result.span_patches["span-1"]
    assert patch is not None
    assert set(patch.delete_attributes) == {
        "langfuse.observation.input",
        "langfuse.observation.output",
        "gen_ai.prompt.0.content",
        "gen_ai.completion.0.content",
        "gen_ai.input.messages",
        "gen_ai.system_instructions",
    }
    assert patch.set_attributes == {}


def test_mask_otel_spans_deletes_metadata_content_keys() -> None:
    span = OtelSpanData(
        trace_id="a" * 32,
        span_id="b" * 16,
        parent_span_id=None,
        name="chat",
        instrumentation_scope_name="langfuse",
        instrumentation_scope_version=None,
        attributes={
            "langfuse.observation.metadata.web_query": '"weather"',
            "langfuse.trace.metadata.snippet": '"article"',
            "langfuse.observation.metadata.category": '"news"',
        },
        resource_attributes={},
    )
    result = mask_otel_spans(params=MaskOtelSpansParams(spans={"span-1": span}))

    assert result is not None
    patch = result.span_patches["span-1"]
    assert patch is not None
    assert set(patch.delete_attributes) == {
        "langfuse.observation.metadata.web_query",
        "langfuse.trace.metadata.snippet",
    }


def test_mask_otel_spans_returns_none_without_content_attributes() -> None:
    span = OtelSpanData(
        trace_id="a" * 32,
        span_id="b" * 16,
        parent_span_id=None,
        name="chat",
        instrumentation_scope_name="langfuse",
        instrumentation_scope_version=None,
        attributes={
            "langfuse.observation.model.name": "mistral/chat-model",
            "gen_ai.usage.input_tokens": 42,
        },
        resource_attributes={},
    )

    assert mask_otel_spans(params=MaskOtelSpansParams(spans={"span-1": span})) is None


def test_call_llm_raises_when_primary_extractor_missing() -> None:
    cfg = AiConfig(
        routes={
            "chat": ModelRoute(
                primary=ModelTarget(model="mistral/chat-model", api_key="chat-key")
            )
        }
    )
    svc = LlmService(cfg)
    with pytest.raises(
        ConfigurationError,
        match="extractor route is required for extraction",
    ):
        asyncio.run(
            svc.call_llm(
                sys_prompt="system",
                user_prompt="user",
                res_model=TlSearchQuery,
                schema_name="triage",
            )
        )


def test_llm_service_init_without_extractor() -> None:
    cfg = AiConfig(
        routes={
            "chat": ModelRoute(
                primary=ModelTarget(
                    model="mistral/chat-model", api_key="chat-key", rpm=60
                )
            ),
            "embed": ModelRoute(
                primary=ModelTarget(
                    model="nvidia_nim/text-embed", api_key="embed-key", rpm=120
                )
            ),
        }
    )
    svc = LlmService(cfg)
    assert svc.rate_limiter is None
    assert svc.embed_rate_limiter is not None
    model_names = [item["model_name"] for item in svc.router.model_list]
    assert "chat" in model_names
    assert "embed" in model_names
    assert "extractor" not in model_names


@patch("litellm.Router.aembedding")
def test_gen_embeddings_uses_embed_route_directly(
    mock_aembedding: AsyncMock,
) -> None:
    cfg = AiConfig(
        routes={
            "embed": ModelRoute(
                primary=ModelTarget(model="nvidia_nim/text-embed", api_key="embed-key")
            )
        }
    )
    mock_res = MagicMock()
    mock_res.data = [{"embedding": [0.1, 0.2, 0.3]}]
    mock_aembedding.return_value = mock_res

    svc = LlmService(cfg)
    results = asyncio.run(svc.gen_embeddings(["test text"]))

    assert results == [[0.1, 0.2, 0.3]]
    mock_aembedding.assert_awaited_once_with(
        model="embed",
        input=["test text"],
        encoding_format="float",
    )
