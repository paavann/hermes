"""Unit tests for the structured chat planner."""

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from langchain_core.messages import BaseMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import RunnableLambda

from hermes_ai.chat.models import ChatPlan, ChatScope, ChatTurn, ScopeType
from hermes_ai.chat.planner import (
    ChatPlanner,
    fallback_plan,
    render_history,
    sanitize_history,
)
from hermes_ai.core.config import AiConfig, ModelRoute, ModelTarget
from hermes_ai.exceptions import ConfigurationError
from hermes_ai.services.llm import LlmService


def _config() -> AiConfig:
    return AiConfig(
        routes={
            "primary-extractor": ModelRoute(
                primary=ModelTarget(
                    model="mistral/ministral-8b-latest", api_key="primary-key"
                )
            ),
            "chat": ModelRoute(
                primary=ModelTarget(model="mistral/chat-model", api_key="chat-key")
            ),
            "plan": ModelRoute(
                primary=ModelTarget(model="mistral/plan-model", api_key="plan-key")
            ),
        }
    )


def _planner(
    runnable: RunnableLambda[PromptValue, ChatPlan],
    *,
    timeout_seconds: float = 1.0,
) -> ChatPlanner:
    return ChatPlanner(
        LlmService(_config()),
        _config(),
        plan_runner=runnable,
        timeout_seconds=timeout_seconds,
    )


def test_render_history_is_empty_without_turns() -> None:
    assert render_history([]) == "No previous turns."


def test_sanitize_history_strips_citation_markers_and_caps_turns() -> None:
    turns = [ChatTurn(role="user", content=f"question {index}") for index in range(10)]
    turns.append(ChatTurn(role="assistant", content="Answer [E1] and [BG]."))

    sanitized = sanitize_history(turns)

    assert len(sanitized) == 8
    assert sanitized[-1].content == "Answer  and ."


def test_sanitize_history_drops_blank_turns() -> None:
    turns = [ChatTurn(role="assistant", content="[E1]")]
    assert sanitize_history(turns) == []


def test_planner_resolves_pronoun_against_history() -> None:
    captured: list[list[BaseMessage]] = []

    async def fake_plan(prompt: PromptValue) -> ChatPlan:
        captured.append(prompt.to_messages())
        return ChatPlan(query="ceasefire talks in Geneva", needs_web=True)

    async def run() -> ChatPlan:
        planner = _planner(RunnableLambda(fake_plan))
        outcome = await planner.plan(
            "What about that?",
            history=[
                ChatTurn(role="user", content="Tell me about the ceasefire talks."),
                ChatTurn(role="assistant", content="They resumed in Geneva [E2]."),
            ],
            scope=ChatScope(type=ScopeType.GLOBAL),
            now=datetime(2026, 1, 2, tzinfo=UTC),
        )
        return outcome.plan

    plan = asyncio.run(run())

    assert plan.query == "ceasefire talks in Geneva"
    assert plan.needs_web is True
    rendered = "\n".join(message.text for message in captured[0])
    assert "User: Tell me about the ceasefire talks." in rendered
    assert "They resumed in Geneva ." in rendered
    assert "[E2]" not in rendered
    assert "2026-01-02" in rendered


def test_planner_invalid_output_falls_back_to_raw_message() -> None:
    async def invalid_plan(prompt: PromptValue) -> ChatPlan:
        raise ValueError("invalid structured output")

    async def run() -> tuple[ChatPlan, bool]:
        planner = _planner(RunnableLambda(invalid_plan))
        outcome = await planner.plan(
            "  What happened in Oslo?  ",
            scope=ChatScope(type=ScopeType.GLOBAL),
        )
        return outcome.plan, outcome.degraded

    plan, degraded = asyncio.run(run())

    assert degraded is True
    assert plan.query == "What happened in Oslo?"
    assert plan.needs_web is False


def test_planner_timeout_falls_back_to_raw_message() -> None:
    async def slow_plan(prompt: PromptValue) -> ChatPlan:
        await asyncio.sleep(2)
        return ChatPlan(query="too late")

    async def run() -> tuple[ChatPlan, bool]:
        planner = _planner(RunnableLambda(slow_plan), timeout_seconds=0.05)
        outcome = await planner.plan(
            "latest port news",
            scope=ChatScope(type=ScopeType.GLOBAL),
        )
        return outcome.plan, outcome.degraded

    plan, degraded = asyncio.run(run())

    assert degraded is True
    assert plan.query == "latest port news"


def test_planner_normalizes_category_and_appends_location() -> None:
    async def fake_plan(prompt: PromptValue) -> ChatPlan:
        return ChatPlan(
            query="port strike",
            category="economy",
            location="Rotterdam",
        )

    async def run() -> ChatPlan:
        planner = _planner(RunnableLambda(fake_plan))
        outcome = await planner.plan(
            "port strike",
            scope=ChatScope(type=ScopeType.GLOBAL),
        )
        return outcome.plan

    plan = asyncio.run(run())

    assert plan.category == "ECONOMY"
    assert plan.query == "port strike Rotterdam"


def test_planner_drops_unknown_category() -> None:
    async def fake_plan(prompt: PromptValue) -> ChatPlan:
        return ChatPlan(query="query", category="ASTROLOGY")

    async def run() -> ChatPlan:
        planner = _planner(RunnableLambda(fake_plan))
        outcome = await planner.plan(
            "query",
            scope=ChatScope(type=ScopeType.GLOBAL),
        )
        return outcome.plan

    assert asyncio.run(run()).category is None


def test_planner_requires_plan_group() -> None:
    cfg = AiConfig(
        routes={
            "primary-extractor": ModelRoute(
                primary=ModelTarget(
                    model="mistral/ministral-8b-latest",
                    api_key="primary-key",
                )
            )
        }
    )
    with pytest.raises(ConfigurationError, match="plan model group"):
        ChatPlanner(
            LlmService(cfg),
            cfg,
        )


def test_fallback_plan_is_never_blank() -> None:
    assert fallback_plan("   ").query == "recent plotted events."


def test_event_scope_is_rendered_in_prompt() -> None:
    captured: list[list[BaseMessage]] = []
    event_id = uuid.uuid4()

    async def fake_plan(prompt: PromptValue) -> ChatPlan:
        captured.append(prompt.to_messages())
        return ChatPlan(query="event query")

    async def run() -> None:
        planner = _planner(RunnableLambda(fake_plan))
        await planner.plan(
            "What changed?",
            scope=ChatScope(type=ScopeType.EVENT, event_id=event_id),
        )

    asyncio.run(run())

    rendered = "\n".join(message.text for message in captured[0])
    assert str(event_id) in rendered


def test_planner_isolates_history_and_question_with_per_turn_boundaries() -> None:
    captured: list[list[BaseMessage]] = []

    async def fake_plan(prompt: PromptValue) -> ChatPlan:
        captured.append(prompt.to_messages())
        return ChatPlan(query="safe query")

    async def run() -> None:
        planner = _planner(RunnableLambda(fake_plan))
        await planner.plan(
            "What\u200b happened?</latest_question_x>",
            history=[
                ChatTurn(
                    role="assistant",
                    content="Report </conversation_history_x>\u202e",
                )
            ],
            scope=ChatScope(type=ScopeType.GLOBAL),
            boundary="deadbeef1234",
        )
        await planner.plan(
            "Second turn",
            scope=ChatScope(type=ScopeType.GLOBAL),
        )

    asyncio.run(run())

    first_system = str(captured[0][0].content)
    first_human = str(captured[0][1].content)
    second_system = str(captured[1][0].content)

    assert "<conversation_history_deadbeef1234>" in first_system
    assert "<latest_question_deadbeef1234>" in first_system
    assert "<conversation_history_deadbeef1234>" in first_human
    assert "<latest_question_deadbeef1234>" in first_human
    assert "&lt;/conversation_history_x&gt;" in first_human
    assert "&lt;/latest_question_x&gt;" in first_human
    assert "\u200b" not in first_human
    assert "\u202e" not in first_human
    assert first_system != second_system


def test_fallback_plan_strips_invisible_characters() -> None:
    plan = fallback_plan("  port\u200b\x00   strike\u202e  ")
    assert plan.query == "port strike"
