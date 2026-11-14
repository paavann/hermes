from __future__ import annotations

import asyncio
import inspect
import logging
import time
import uuid
from collections import Counter
from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    BaseMessageChunk,
    HumanMessage,
    RemoveMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Overwrite

from hermes_ai.chat.citations import (
    CitationRegistry,
    CitationStreamFilter,
    CitationValidation,
    finalize_answer,
)
from hermes_ai.chat.models.events import (
    ChatStage,
    ChatUsage,
    DoneEvent,
    EngineEvent,
    ErrorCode,
    ErrorEvent,
    Provenance,
    SourcesEvent,
    StatusEvent,
    TokenEvent,
)
from hermes_ai.chat.models.plan import ChatPlan, Planner
from hermes_ai.chat.models.retrieval import (
    ChatRetriever,
    Coverage,
    CoverageLevel,
    DegradedFlag,
    RetrievalFilters,
    RetrievalResult,
    RetrievedEvidence,
)
from hermes_ai.chat.models.scopes import ChatRole, ChatScope, ChatTurn
from hermes_ai.chat.models.sources import (
    ChatSource,
    ChatSourceKind,
    GroundingFlag,
    WebResult,
)
from hermes_ai.chat.planner import (
    CITATION_MARKER_RE,
    MAX_HISTORY_TURNS,
)
from hermes_ai.chat.prompts import build_answer_messages
from hermes_ai.chat.state import ChatState
from hermes_ai.chat.web import WebSearcher
from hermes_ai.core.config import AiConfig
from hermes_ai.exceptions import ConfigurationError
from hermes_ai.services.llm import LlmService
from hermes_ai.utils.sanitization import clean_invisible_chars


logger = logging.getLogger(__name__)

RETRIEVAL_TIMEOUT_SECONDS = 10.0
FIRST_TOKEN_TIMEOUT_SECONDS = 30.0
TOTAL_STREAM_TIMEOUT_SECONDS = 120.0
RECURSION_LIMIT = 12





class AnswerModel(Protocol):
    def astream(
        self, input: Sequence[BaseMessage]
    ) -> AsyncIterator[BaseMessageChunk]: ...


def _plan_filters(plan: ChatPlan) -> RetrievalFilters | None:
    if plan.category is None and plan.time_range is None:
        return None
    return RetrievalFilters(
        category=plan.category,
        start=plan.time_range.start if plan.time_range else None,
        end=plan.time_range.end if plan.time_range else None,
    )


async def _close_stream(stream: AsyncIterator[BaseMessageChunk] | None) -> None:
    if stream is None:
        return
    aclose = getattr(stream, "aclose", None)
    if not callable(aclose):
        return
    result = aclose()
    if inspect.isawaitable(result):
        await result


def _message_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict):
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts)


def _chunk_text(chunk: BaseMessageChunk) -> str:
    content = chunk.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


def _int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _merge_usage(
    current: ChatUsage | None, chunk: BaseMessageChunk
) -> ChatUsage | None:
    usage_metadata = getattr(chunk, "usage_metadata", None)
    if isinstance(usage_metadata, dict):
        merged = ChatUsage(
            prompt_tokens=_int(usage_metadata.get("input_tokens")),
            completion_tokens=_int(usage_metadata.get("output_tokens")),
            total_tokens=_int(usage_metadata.get("total_tokens")),
        )
        if merged.total_tokens or merged.prompt_tokens or merged.completion_tokens:
            return merged
    response_metadata = getattr(chunk, "response_metadata", None)
    if isinstance(response_metadata, dict):
        usage = response_metadata.get("usage")
        if isinstance(usage, dict):
            merged = ChatUsage(
                prompt_tokens=_int(usage.get("prompt_tokens")),
                completion_tokens=_int(usage.get("completion_tokens")),
                total_tokens=_int(usage.get("total_tokens")),
            )
            if merged.total_tokens or merged.prompt_tokens or merged.completion_tokens:
                return merged
    return current


def _add_usage(first: ChatUsage | None, second: ChatUsage | None) -> ChatUsage | None:
    if first is None:
        return second
    if second is None:
        return first
    return ChatUsage(
        prompt_tokens=first.prompt_tokens + second.prompt_tokens,
        completion_tokens=first.completion_tokens + second.completion_tokens,
        total_tokens=first.total_tokens + second.total_tokens,
    )


def _state_usage(state: ChatState) -> ChatUsage | None:
    raw = state.get("usage") or {}
    if not raw:
        return None
    usage = ChatUsage.model_validate(raw)
    if not (usage.total_tokens or usage.prompt_tokens or usage.completion_tokens):
        return None
    return usage


def _usage_update(usage: ChatUsage | None, state: ChatState) -> dict[str, int]:
    if usage is None:
        return dict(state.get("usage") or {})
    return usage.model_dump()


def _split_turn(
    messages: Sequence[BaseMessage],
) -> tuple[Sequence[BaseMessage], Sequence[BaseMessage]]:
    for index in range(len(messages) - 1, -1, -1):
        if isinstance(messages[index], HumanMessage):
            return messages[:index], messages[index:]
    return (), messages


def _history_messages(messages: Sequence[BaseMessage]) -> list[BaseMessage]:
    prior, _ = _split_turn(messages)
    history: list[BaseMessage] = []
    for message in prior:
        if isinstance(message, HumanMessage):
            text = _message_text(message).strip()
            if text:
                history.append(HumanMessage(content=text))
            continue
        if not isinstance(message, AIMessage) or message.tool_calls:
            continue
        stripped = CITATION_MARKER_RE.sub("", _message_text(message))
        text = clean_invisible_chars(stripped, preserve_newlines=True).strip()
        if text:
            history.append(AIMessage(content=text))
    return history[-MAX_HISTORY_TURNS:]


def _history_turns(messages: Sequence[BaseMessage]) -> list[ChatTurn]:
    return [
        ChatTurn(
            role=(
                ChatRole.USER
                if isinstance(message, HumanMessage)
                else ChatRole.ASSISTANT
            ),
            content=_message_text(message),
        )
        for message in _history_messages(messages)
    ]


def _evidence(state: ChatState, retrieval: RetrievalResult) -> list[RetrievedEvidence]:
    combined = list(retrieval.evidence)
    combined.extend(
        RetrievedEvidence.model_validate(item)
        for item in state.get("extra_evidence") or []
    )
    seen: set[uuid.UUID] = set()
    unique: list[RetrievedEvidence] = []
    for item in combined:
        if item.event_id in seen:
            continue
        seen.add(item.event_id)
        unique.append(item)
    return unique


def _web_results(state: ChatState) -> list[WebResult]:
    results = [
        WebResult.model_validate(item) for item in state.get("web_results") or []
    ]
    seen: set[str] = set()
    unique: list[WebResult] = []
    for item in results:
        if item.url in seen:
            continue
        seen.add(item.url)
        unique.append(item)
    return unique


def _registry(state: ChatState, retrieval: RetrievalResult) -> CitationRegistry:
    return CitationRegistry.build(_evidence(state, retrieval), _web_results(state))


def _provenance(
    sources: Sequence[ChatSource], validation: CitationValidation
) -> Provenance:
    kinds: Counter[ChatSourceKind] = Counter(source.kind for source in sources)
    grounding: list[GroundingFlag] = []
    if not validation.has_citation and not validation.has_background:
        grounding.append(GroundingFlag.MISSING_CITATIONS)
    return Provenance(
        events=kinds[ChatSourceKind.EVENT],
        articles=kinds[ChatSourceKind.ARTICLE],
        timeline_nodes=kinds[ChatSourceKind.TIMELINE],
        web=kinds[ChatSourceKind.WEB],
        background=validation.has_background,
        grounding=grounding,
    )


class ChatEngine:
    def __init__(
        self,
        llm: LlmService,
        config: AiConfig,
        *,
        retriever: ChatRetriever,
        planner: Planner,
        answer_model: AnswerModel,
        tools: Sequence[BaseTool] = (),
        web_search: WebSearcher | None = None,
        checkpointer: BaseCheckpointSaver[str] | None = None,
        retrieval_timeout_seconds: float = RETRIEVAL_TIMEOUT_SECONDS,
        first_token_timeout_seconds: float = FIRST_TOKEN_TIMEOUT_SECONDS,
        total_timeout_seconds: float = TOTAL_STREAM_TIMEOUT_SECONDS,
    ) -> None:
        if not config.has_chat:
            raise ConfigurationError(
                "conversational chat requires a configured chat model group."
            )
        if not config.has_plan:
            raise ConfigurationError(
                "conversational chat requires a configured plan model group."
            )
        self._llm = llm
        self._config = config
        self._retriever = retriever
        self._planner = planner
        self._answer_model = answer_model
        self._tools = tuple(tools)
        self._web = web_search
        self._retrieval_timeout_seconds = retrieval_timeout_seconds
        self._first_token_timeout_seconds = first_token_timeout_seconds
        self._total_timeout_seconds = total_timeout_seconds
        self._graph = self._build_graph(checkpointer or InMemorySaver())

    @property
    def llm(self) -> LlmService:
        return self._llm

    @property
    def config(self) -> AiConfig:
        return self._config

    @property
    def retriever(self) -> ChatRetriever:
        return self._retriever

    @property
    def web_configured(self) -> bool:
        return self._web is not None

    def _needs_web(self, plan: ChatPlan, coverage: Coverage) -> bool:
        if self._web is None:
            return plan.needs_web or coverage.level in {
                CoverageLevel.EMPTY,
                CoverageLevel.THIN,
            }
        return (
            plan.needs_web
            or coverage.level in {CoverageLevel.EMPTY, CoverageLevel.THIN}
            or (plan.recency_intent and coverage.recency_stale)
        )

    async def _plan(self, state: ChatState) -> dict[str, object]:
        writer = get_stream_writer()
        writer(StatusEvent(stage=ChatStage.ACCEPTED))
        writer(StatusEvent(stage=ChatStage.PLANNING))
        messages = state["messages"]
        current = _message_text(messages[-1])
        scope = ChatScope.model_validate(state["scope"])
        outcome = await self._planner.plan(
            current,
            history=_history_turns(messages),
            scope=scope,
        )
        degraded = [DegradedFlag.PLANNER_FALLBACK.value] if outcome.degraded else []
        return {
            "query": outcome.plan.query,
            "plan": outcome.plan.model_dump(mode="json"),
            "started_at": time.monotonic(),
            "web_available": False,
            "answer": "",
            "usage": {},
            "error": None,
            "web_results": Overwrite([]),
            "extra_evidence": Overwrite([]),
            "degraded": Overwrite(degraded),
        }

    async def _retrieve(self, state: ChatState) -> dict[str, object]:
        get_stream_writer()(StatusEvent(stage=ChatStage.RETRIEVING))
        plan = ChatPlan.model_validate(state["plan"])
        scope = ChatScope.model_validate(state["scope"])
        try:
            async with asyncio.timeout(self._retrieval_timeout_seconds):
                retrieval = await self._retriever.retrieve(
                    plan.query,
                    scope=scope,
                    filters=_plan_filters(plan),
                    recency_intent=plan.recency_intent,
                )
        except Exception as exc:
            is_timeout = isinstance(exc, TimeoutError)
            if is_timeout:
                logger.error("chat retrieval timed out.")
            else:
                logger.error("chat retrieval failed: %s.", exc)
            get_stream_writer()(
                ErrorEvent(
                    code=ErrorCode.RETRIEVAL_FAILED,
                    message=(
                        "Local retrieval timed out."
                        if is_timeout
                        else "Local retrieval failed."
                    ),
                    retryable=True,
                )
            )
            return {"error": ErrorCode.RETRIEVAL_FAILED.value}
        return {
            "retrieval": retrieval.model_dump(mode="json"),
            "degraded": [flag.value for flag in retrieval.degraded],
        }

    async def _search(self, state: ChatState) -> dict[str, object]:
        get_stream_writer()(StatusEvent(stage=ChatStage.SEARCHING))
        plan = ChatPlan.model_validate(state["plan"])
        if self._web is None:
            return {
                "web_available": False,
                "degraded": [DegradedFlag.WEB_UNAVAILABLE.value],
            }
        outcome = await self._web.search(
            plan.web_query or plan.query,
            recency_intent=plan.recency_intent,
        )
        update: dict[str, object] = {"web_available": not outcome.degraded}
        if outcome.results:
            update["web_results"] = [
                result.model_dump(mode="json") for result in outcome.results
            ]
        if outcome.degraded:
            update["degraded"] = [DegradedFlag.WEB_UNAVAILABLE.value]
        return update

    async def _generate(self, state: ChatState) -> dict[str, object]:
        get_stream_writer()(StatusEvent(stage=ChatStage.GENERATING))
        scope = ChatScope.model_validate(state["scope"])
        retrieval = RetrievalResult.model_validate(state["retrieval"])
        registry = _registry(state, retrieval)
        _, current_turn = _split_turn(state["messages"])
        question = _message_text(current_turn[0]) if current_turn else ""
        messages = build_answer_messages(
            registry=registry,
            message=question,
            scope=scope,
            web_available=bool(state.get("web_available")),
            coverage=retrieval.coverage,
            history=_history_messages(state["messages"]),
            tools_available=bool(self._tools),
        )
        messages.extend(current_turn[1:])

        filter_ = CitationStreamFilter(registry)
        parts: list[str] = []
        usage = _state_usage(state)
        pass_usage: ChatUsage | None = None
        accumulated: AIMessageChunk | None = None
        stream: AsyncIterator[BaseMessageChunk] | None = None
        first_token = True
        deadline = float(state.get("started_at") or time.monotonic()) + (
            self._total_timeout_seconds
        )
        try:
            stream = self._answer_model.astream(messages)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    get_stream_writer()(
                        ErrorEvent(
                            code=ErrorCode.STREAM_TIMEOUT,
                            message="The answer stream exceeded its time limit.",
                            retryable=True,
                        )
                    )
                    return {
                        "error": ErrorCode.STREAM_TIMEOUT.value,
                        "usage": _usage_update(usage, state),
                    }
                token_timeout = (
                    min(remaining, self._first_token_timeout_seconds)
                    if first_token
                    else remaining
                )
                try:
                    async with asyncio.timeout(token_timeout):
                        chunk = await anext(stream)
                except StopAsyncIteration:
                    break
                except TimeoutError:
                    logger.warning("chat answer stream timed out.")
                    get_stream_writer()(
                        ErrorEvent(
                            code=(
                                ErrorCode.MODEL_TIMEOUT
                                if first_token
                                else ErrorCode.STREAM_TIMEOUT
                            ),
                            message="The answer model did not respond in time.",
                            retryable=True,
                        )
                    )
                    return {
                        "error": (
                            ErrorCode.MODEL_TIMEOUT.value
                            if first_token
                            else ErrorCode.STREAM_TIMEOUT.value
                        ),
                        "usage": _usage_update(usage, state),
                    }
                except Exception as exc:
                    logger.error("chat answer stream failed: %s.", exc)
                    get_stream_writer()(
                        ErrorEvent(
                            code=ErrorCode.MODEL_FAILED,
                            message="The answer model failed.",
                            retryable=True,
                        )
                    )
                    return {
                        "error": ErrorCode.MODEL_FAILED.value,
                        "usage": _usage_update(usage, state),
                    }

                if isinstance(chunk, AIMessageChunk):
                    accumulated = chunk if accumulated is None else accumulated + chunk
                pass_usage = _merge_usage(pass_usage, chunk)
                text = _chunk_text(chunk)
                if not text:
                    continue
                first_token = False
                cleaned = filter_.feed(text)
                if cleaned:
                    parts.append(cleaned)
                    get_stream_writer()(TokenEvent(text=cleaned))
        except Exception as exc:
            logger.error("chat answer stream failed: %s.", exc)
            get_stream_writer()(
                ErrorEvent(
                    code=ErrorCode.MODEL_FAILED,
                    message="The answer model failed.",
                    retryable=True,
                )
            )
            return {
                "error": ErrorCode.MODEL_FAILED.value,
                "usage": _usage_update(usage, state),
            }
        finally:
            await _close_stream(stream)

        tail = filter_.flush()
        if tail:
            parts.append(tail)
            get_stream_writer()(TokenEvent(text=tail))

        generated = "".join(parts)
        tool_calls = list(accumulated.tool_calls) if accumulated is not None else []
        answer = f"{state.get('answer') or ''}{generated}"
        usage = _add_usage(usage, pass_usage)
        update: dict[str, object] = {
            "messages": [AIMessage(content=generated, tool_calls=tool_calls)],
            "answer": answer,
            "usage": _usage_update(usage, state),
        }
        if tool_calls and not self._tools:
            logger.error("answer model requested tools but none are bound.")
            get_stream_writer()(
                ErrorEvent(
                    code=ErrorCode.MODEL_FAILED,
                    message="The answer model requested an unavailable tool.",
                    retryable=True,
                )
            )
            update["error"] = ErrorCode.MODEL_FAILED.value
        return update

    def _build_graph(
        self, checkpointer: BaseCheckpointSaver[str]
    ) -> CompiledStateGraph[ChatState, None, ChatState, ChatState]:
        graph = StateGraph(ChatState)
        graph.add_node("plan", self._plan)
        graph.add_node("retrieve", self._retrieve)
        graph.add_node("search", self._search)
        graph.add_node("generate", self._generate)
        graph.add_node("finalize", self._finalize)
        graph.add_node("tools", ToolNode(self._tools))
        graph.add_edge(START, "plan")
        graph.add_edge("plan", "retrieve")
        graph.add_conditional_edges(
            "retrieve",
            self._after_retrieve,
            {"search": "search", "generate": "generate", END: END},
        )
        graph.add_edge("search", "generate")
        graph.add_conditional_edges(
            "generate",
            self._after_generate,
            {"finalize": "finalize", "tools": "tools", END: END}
        )
        graph.add_edge("tools", "generate")            
        graph.add_edge("finalize", END)
        return graph.compile(checkpointer=checkpointer)

    async def _finalize(self, state: ChatState) -> dict[str, object]:
        get_stream_writer()(StatusEvent(stage=ChatStage.FINALIZING))
        retrieval = RetrievalResult.model_validate(state["retrieval"])
        registry = _registry(state, retrieval)
        validation = finalize_answer(str(state.get("answer") or ""), registry)
        sources = registry.sources_for(validation.cited_markers)
        provenance = _provenance(sources, validation)
        flags = {DegradedFlag(value) for value in state.get("degraded") or []}
        degraded = tuple(sorted(flags, key=lambda flag: flag.value))
        get_stream_writer()(SourcesEvent(sources=tuple(sources)))
        get_stream_writer()(
            DoneEvent(
                provenance=provenance,
                coverage=retrieval.coverage,
                usage=_state_usage(state),
                web_used=bool(state.get("web_results")),
                degraded=degraded,
            )
        )
        return {}

    def _after_retrieve(self, state: ChatState) -> str:
        if state.get("error"):
            return END
        plan = ChatPlan.model_validate(state["plan"])
        retrieval = RetrievalResult.model_validate(state["retrieval"])
        if self._needs_web(plan, retrieval.coverage):
            return "search"
        return "generate"

    def _after_generate(self, state: ChatState) -> str:
        if state.get("error"):
            return END
        messages = state["messages"]
        last = messages[-1] if messages else None
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools" if self._tools else END
        return "finalize"

    async def _discard_last_turn(self, thread_id: str) -> None:
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        snapshot = await self._graph.aget_state(config)
        messages = snapshot.values.get("messages")
        if not isinstance(messages, list):
            return
        index = -1
        for position in range(len(messages) - 1, -1, -1):
            if isinstance(messages[position], HumanMessage):
                index = position
                break
        if index < 0:
            return
        removals = [
            RemoveMessage(id=message.id)
            for message in messages[index:]
            if message.id is not None
        ]
        if removals:
            await self._graph.aupdate_state(config, {"messages": removals})

    async def stream(
        self,
        message: str,
        *,
        thread_id: str,
        scope: ChatScope,
        retry: bool = False,
    ) -> AsyncIterator[EngineEvent]:
        if retry:
            await self._discard_last_turn(thread_id)
        config: RunnableConfig = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": RECURSION_LIMIT,
        }
        initial: ChatState = {
            "messages": [HumanMessage(content=message)],
            "scope": scope.model_dump(mode="json"),
            "query": message,
            "plan": {},
            "retrieval": {},
            "web_available": False,
            "answer": "",
            "usage": {},
            "error": None,
            "started_at": time.monotonic(),
            "web_results": [],
            "extra_evidence": [],
            "degraded": [],
        }
        try:
            async for event in self._graph.astream(
                initial, config, stream_mode="custom"
            ):
                if isinstance(event, EngineEvent):
                    yield event
        except GraphRecursionError:
            logger.error("chat graph exceeded its recursion limit.")
            yield ErrorEvent(
                code=ErrorCode.MODEL_FAILED,
                message="The answer model exceeded its tool-call limit.",
                retryable=True,
            )
        except Exception:
            logger.exception("chat graph failed.")
            yield ErrorEvent(
                code=ErrorCode.INTERNAL_ERROR,
                message="The chat stream failed unexpectedly.",
                retryable=True,
            )


__all__ = ["AnswerModel", "ChatEngine", "Planner"]
