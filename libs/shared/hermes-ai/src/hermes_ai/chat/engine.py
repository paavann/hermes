from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections import Counter
from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from langchain_core.messages import BaseMessage, BaseMessageChunk

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
from hermes_ai.chat.models.plan import ChatPlan
from hermes_ai.chat.models.retrieval import (
    Coverage,
    CoverageLevel,
    DegradedFlag,
    RetrievalFilters,
)
from hermes_ai.chat.models.scopes import ChatScope, ChatTurn
from hermes_ai.chat.models.sources import (
    ChatSource,
    ChatSourceKind,
    GroundingFlag,
)
from hermes_ai.chat.planner import PlannerOutcome
from hermes_ai.chat.prompts import build_answer_messages
from hermes_ai.chat.retriever import ChatRetriever
from hermes_ai.chat.web import WebSearchOutcome
from hermes_ai.core.config import AiConfig
from hermes_ai.exceptions import ConfigurationError
from hermes_ai.services.llm import LlmService


logger = logging.getLogger(__name__)

RETRIEVAL_TIMEOUT_SECONDS = 10.0
FIRST_TOKEN_TIMEOUT_SECONDS = 30.0
TOTAL_STREAM_TIMEOUT_SECONDS = 120.0


class Planner(Protocol):
    async def plan(
        self,
        message: str,
        *,
        history: Sequence[ChatTurn] = (),
        scope: ChatScope,
    ) -> PlannerOutcome: ...


class WebSearcher(Protocol):
    async def search(
        self,
        query: str,
        *,
        recency_intent: bool = False,
    ) -> WebSearchOutcome: ...


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
        web_search: WebSearcher | None = None,
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
        self._web = web_search
        self._retrieval_timeout_seconds = retrieval_timeout_seconds
        self._first_token_timeout_seconds = first_token_timeout_seconds
        self._total_timeout_seconds = total_timeout_seconds

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

    async def stream(
        self,
        message: str,
        *,
        history: Sequence[ChatTurn] = (),
        scope: ChatScope,
    ) -> AsyncIterator[EngineEvent]:
        # acceptance phase.
        yield StatusEvent(stage=ChatStage.ACCEPTED)
        start = time.monotonic()
        degraded: set[DegradedFlag] = set()

        # planning phase.
        yield StatusEvent(stage=ChatStage.PLANNING)
        planner_outcome = await self._planner.plan(
            message, history=history, scope=scope
        )
        plan = planner_outcome.plan
        if planner_outcome.degraded:
            degraded.add(DegradedFlag.PLANNER_FALLBACK)

        # retrieval phase.
        yield StatusEvent(stage=ChatStage.RETRIEVING)
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
            yield ErrorEvent(
                code=ErrorCode.RETRIEVAL_FAILED,
                message="Local retrieval timed out."
                if is_timeout
                else "Local retrieval failed.",
                retryable=True,
            )
            return
        degraded.update(retrieval.degraded)

        # searching phase (conditional).
        web_results = ()
        web_used = False
        web_gate = self._needs_web(plan, retrieval.coverage)
        if web_gate:
            yield StatusEvent(stage=ChatStage.SEARCHING)
            if self._web is None:
                degraded.add(DegradedFlag.WEB_UNAVAILABLE)
            else:
                web_outcome = await self._web.search(
                    plan.web_query or plan.query,
                    recency_intent=plan.recency_intent,
                )
                web_results = tuple(web_outcome.results)
                web_used = bool(web_results)
                if web_outcome.degraded:
                    degraded.add(DegradedFlag.WEB_UNAVAILABLE)
        web_available = web_gate and DegradedFlag.WEB_UNAVAILABLE not in degraded

        # generation phase.
        registry = CitationRegistry.build(retrieval.evidence, web_results)
        yield StatusEvent(stage=ChatStage.GENERATING)
        messages = build_answer_messages(
            registry=registry,
            message=message,
            scope=scope,
            web_available=web_available,
            coverage=retrieval.coverage,
        )
        filter_ = CitationStreamFilter(registry)
        answer_parts: list[str] = []
        usage: ChatUsage | None = None
        stream: AsyncIterator[BaseMessageChunk] | None = None
        first_token = True
        deadline = start + self._total_timeout_seconds
        try:
            stream = self._answer_model.astream(messages)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    yield ErrorEvent(
                        code=ErrorCode.STREAM_TIMEOUT,
                        message="The answer stream exceeded its time limit.",
                        retryable=True,
                    )
                    return
                token_timeout = (
                    min(remaining, self._first_token_timeout_seconds)
                    if first_token
                    else remaining
                )
                try:
                    async with asyncio.timeout(token_timeout):
                        chunk = await anext(stream)
                except Exception as exc:
                    if isinstance(exc, StopAsyncIteration):
                        break
                    elif isinstance(exc, TimeoutError):
                        logger.warning("chat answer stream timed out.")
                        yield ErrorEvent(
                            code=(
                                ErrorCode.MODEL_TIMEOUT
                                if first_token
                                else ErrorCode.STREAM_TIMEOUT
                            ),
                            message="The answer model did not respond in time.",
                            retryable=True,
                        )
                    else:
                        logger.error("chat answer stream failed: %s.", exc)
                        yield ErrorEvent(
                            code=ErrorCode.MODEL_FAILED,
                            message="The answer model failed.",
                            retryable=True,
                        )
                    return
                usage = _merge_usage(usage, chunk)
                text = _chunk_text(chunk)
                if not text:
                    continue
                first_token = False
                cleaned = filter_.feed(text)
                if cleaned:
                    answer_parts.append(cleaned)
                    yield TokenEvent(text=cleaned)
        except Exception as exc:
            logger.error("chat answer stream failed: %s.", exc)
            yield ErrorEvent(
                code=ErrorCode.MODEL_FAILED,
                message="The answer model failed.",
                retryable=True,
            )
            return
        finally:
            await _close_stream(stream)

        tail = filter_.flush()
        if tail:
            answer_parts.append(tail)
            yield TokenEvent(text=tail)
        yield StatusEvent(stage=ChatStage.FINALIZING)
        validation = finalize_answer("".join(answer_parts), registry)
        sources = registry.sources_for(validation.cited_markers)
        provenance = _provenance(sources, validation)
        ordered_degraded = tuple(sorted(degraded, key=lambda flag: flag.value))
        yield SourcesEvent(sources=tuple(sources))
        yield DoneEvent(
            provenance=provenance,
            coverage=retrieval.coverage,
            usage=usage,
            web_used=web_used,
            degraded=ordered_degraded,
        )


__all__ = ["AnswerModel", "ChatEngine", "Planner", "WebSearcher"]
