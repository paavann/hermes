"""Tests for the lazy HermesAi chat engine factory wiring."""

import pytest

from hermes_ai.chat.engine import ChatEngine
from hermes_ai.chat.models import ChatScope, RetrievalFilters, RetrievalResult
from hermes_ai.client import HermesAi
from hermes_ai.core.config import AiConfig, ModelRoute, ModelTarget
from hermes_ai.exceptions import ConfigurationError


class DummyRetriever:
    async def retrieve(
        self,
        query: str,
        *,
        scope: ChatScope,
        filters: RetrievalFilters | None = None,
        recency_intent: bool = False,
    ) -> RetrievalResult:
        raise NotImplementedError


def _config(
    *,
    chat: bool = True,
    plan: bool = True,
    tavily: str | None = None,
) -> AiConfig:
    routes = {
        "primary-extractor": ModelRoute(
            primary=ModelTarget(
                model="mistral/ministral-8b-latest", api_key="primary-key"
            )
        ),
    }
    if chat:
        routes["chat"] = ModelRoute(
            primary=ModelTarget(model="mistral/chat-model", api_key="chat-key")
        )
    if plan:
        routes["plan"] = ModelRoute(
            primary=ModelTarget(model="mistral/plan-model", api_key="plan-key")
        )
    return AiConfig(
        routes=routes,
        tavily_api_key=tavily,
    )


def test_create_chat_engine_builds_engine() -> None:
    client = HermesAi(_config())
    retriever = DummyRetriever()

    engine = client.create_chat_engine(retriever)

    assert isinstance(engine, ChatEngine)
    assert engine.retriever is retriever
    assert engine.web_configured is False


def test_create_chat_engine_enables_web_when_tavily_is_configured() -> None:
    client = HermesAi(_config(tavily="test-key"))

    engine = client.create_chat_engine(DummyRetriever())

    assert engine.web_configured is True


def test_create_chat_engine_requires_chat_group() -> None:
    client = HermesAi(_config(chat=False))

    with pytest.raises(ConfigurationError, match="chat model group"):
        _ = client.create_chat_engine(DummyRetriever())


def test_create_chat_engine_requires_plan_group() -> None:
    client = HermesAi(_config(plan=False))

    with pytest.raises(ConfigurationError, match="plan model group"):
        _ = client.create_chat_engine(DummyRetriever())
