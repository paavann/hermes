"""Unit tests for hermes_worker.core.ai client construction."""

import asyncio
from hermes_ai.client import HermesAi
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


class TestWorkerAiClientFactory:
    def test_create_ai_client_success(self) -> None:
        client = create_ai_client(_settings())

        assert isinstance(client, HermesAi)
        assert (
            client.config.routes["extractor"].primary.model == "mistral/mistral-large"
        )
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

    def test_task_routes_default_to_primary_llm_route(self) -> None:
        client = create_ai_client(_settings())

        for task in ("label", "adjudicate", "describe", "relationship"):
            route = client.config.routes[task]
            assert route.primary.model == "mistral/mistral-large"
            assert route.primary.api_key == "mock-llm-key"
            assert route.primary.rpm == 26

    def test_task_routes_accept_model_and_key_overrides(self) -> None:
        client = create_ai_client(
            _settings(
                LABEL_MODEL="mistral/ministral-8b-latest",
                LABEL_API="label-key",
                DESCRIBE_MODEL="mistral/mistral-medium",
            )
        )

        label = client.config.routes["label"].primary
        describe = client.config.routes["describe"].primary
        adjudicate = client.config.routes["adjudicate"].primary

        assert label.model == "mistral/ministral-8b-latest"
        assert label.api_key == "label-key"
        assert describe.model == "mistral/mistral-medium"
        assert describe.api_key == "mock-llm-key"
        assert adjudicate.model == "mistral/mistral-large"

    def test_task_routes_keep_fallback_chain(self) -> None:
        client = create_ai_client(
            _settings(
                LLM_MODEL_1="mistral/ministral-8b-latest",
                LLM_API_1="fallback-llm-key",
            )
        )

        fallbacks = client.config.routes["label"].fallbacks
        assert len(fallbacks) == 1
        assert fallbacks[0].api_key == "fallback-llm-key"

    def test_gen_embeddings_empty_input(self) -> None:
        async def run() -> None:
            client = create_ai_client(_settings())
            res = await client.llm.gen_embeddings([], input_type="passage")
            assert res == []

        asyncio.run(run())

    def test_gen_embeddings_without_route_degrades_to_none(self) -> None:
        async def run() -> None:
            client = create_ai_client(_settings(EMBED_API="", EMBED_MODEL=""))
            res = await client.llm.gen_embeddings(["alpha", "beta"], input_type="passage")
            assert res == [None, None]

        asyncio.run(run())


    def test_create_ai_client_forwards_model_kwargs_and_timeout(self) -> None:
        settings = _settings(
            LLM_MODEL_KWARGS={
                "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}
            },
            DESCRIBE_MODEL_KWARGS={"temperature": 0},
            LLM_REQUEST_TIMEOUT_SECONDS=45.0,
        )
        client = create_ai_client(settings)

        assert settings.EVENT_DESCRIBE_BATCH_SIZE == 5
        describe = client.config.routes["describe"].primary
        adjudicate = client.config.routes["adjudicate"].primary
        assert describe.model_kwargs == {"temperature": 0}
        assert describe.timeout_seconds == 45.0
        assert adjudicate.model_kwargs == {
            "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}
        }
        assert adjudicate.timeout_seconds == 45.0
