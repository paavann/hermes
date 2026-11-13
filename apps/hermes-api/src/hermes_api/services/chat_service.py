from __future__ import annotations
import asyncio
import inspect
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from fastapi import Request
from hermes_ai import HermesAi
from hermes_ai.chat.engine import ChatEngine
from hermes_ai.chat.models import (
    BoundingBox as EngineBoundingBox,
)
from hermes_ai.chat.models import (
    ChatRole,
    ChatScope,
    ChatStage,
    ChatTurn,
    DoneEvent,
    EngineEvent,
    ErrorCode,
    ErrorEvent,
    ScopeType,
    SourcesEvent,
    StatusEvent,
    TokenEvent,
)
from hermes_ai.chat.models import (
    ChatSource as EngineSource,
)
from hermes_ai.chat.models import (
    ChatUsage as EngineUsage,
)
from hermes_ai.exceptions import ConfigurationError
from hermes_api.core.config import Settings
from hermes_api.schemas.chat import (
    ChatCoverage,
    ChatDoneEvent,
    ChatErrorEvent,
    ChatEventScope,
    ChatHistoryMessage,
    ChatProvenance,
    ChatRequest,
    ChatSource,
    ChatSourcesEvent,
    ChatStatusEvent,
    ChatTokenEvent,
    ChatUsage,
    ChatViewportScope,
)
from hermes_api.services.ai_service import AiService
from hermes_api.services.chat_guards import (
    BudgetReservation,
    ChatGuards,
    estimate_tokens,
)
from hermes_api.services.chat_retriever import DbChatRetriever


logger = logging.getLogger(__name__)

KEEPALIVE_SECONDS = 10.0
KEEPALIVE_COMMENT = ": keepalive\n\n"
DISCONNECT_POLL_SECONDS = 0.5


async def _next_event(iterator: AsyncIterator[EngineEvent]) -> EngineEvent:
    """Wrap ``anext`` in a coroutine so ``asyncio.create_task`` accepts it."""
    return await anext(iterator)


async def _wait_disconnect(request: Request) -> None:
    """Poll for client disconnect so in-flight streaming tasks can be aborted."""
    while True:
        if await request.is_disconnected():
            return
        await asyncio.sleep(DISCONNECT_POLL_SECONDS)


@dataclass(slots=True)
class PreparedTurn:
    message: str
    history: tuple[ChatTurn, ...]
    scope: ChatScope
    reservation: BudgetReservation
    guards: ChatGuards
    _settled: bool = field(default=False, init=False)

    def settle(self, actual_tokens: int | None) -> None:
        if self._settled:
            return
        self._settled = True
        self.guards.concurrency.release()
        if actual_tokens is None:
            self.reservation.release()
        else:
            self.reservation.reconcile(actual_tokens)


class ChatRuntime:
    def __init__(
        self,
        ai: HermesAi,
        engine: ChatEngine,
        guards: ChatGuards,
        *,
        max_output_tokens: int,
        owns_ai: bool = True,
    ) -> None:
        self._ai = ai
        self._engine = engine
        self._guards = guards
        self._max_output_tokens = max_output_tokens
        self._owns_ai = owns_ai

    @property
    def engine(self) -> ChatEngine:
        return self._engine

    @property
    def guards(self) -> ChatGuards:
        return self._guards

    @property
    def max_output_tokens(self) -> int:
        return self._max_output_tokens

    @classmethod
    def from_settings(
        cls,
        config: Settings,
        *,
        ai_service: AiService | None = None,
    ) -> ChatRuntime | None:
        if not config.CHAT_ENABLED:
            logger.info("conversational chat is disabled by configuration.")
            return None

        owns_ai = ai_service is None
        if ai_service is None:
            try:
                ai_service = AiService(config)
            except ValueError:
                logger.warning(
                    "chat model credentials are missing; chat will return 503."
                )
                return None

        ai = ai_service.client
        if not ai.config.has_chat or not ai.config.has_plan:
            logger.warning("chat model credentials are missing; chat will return 503.")
            return None

        try:
            retriever = DbChatRetriever(
                ai.llm,
                top_k=config.CHAT_RETRIEVAL_TOP_K,
                min_local_results=config.CHAT_MIN_LOCAL_RESULTS,
                min_semantic_similarity=config.CHAT_MIN_SEMANTIC_SIMILARITY,
                freshness_hours=float(config.CHAT_FRESHNESS_HOURS),
            )
            engine = ai.create_chat_engine(retriever)
        except (ConfigurationError, ValueError) as exc:
            logger.error("chat runtime is unavailable: %s.", exc)
            return None

        guards = ChatGuards(
            rate_limit_requests=config.CHAT_RATE_LIMIT_REQUESTS,
            rate_limit_window_seconds=float(config.CHAT_RATE_LIMIT_WINDOW_SECONDS),
            daily_token_budget=config.CHAT_DAILY_TOKEN_BUDGET,
            max_concurrent=config.CHAT_MAX_CONCURRENT,
            queue_timeout_seconds=config.CHAT_QUEUE_TIMEOUT_SECONDS,
            trust_proxy_headers=config.TRUST_PROXY_HEADERS,
        )

        chat_route = ai.config.routes["chat"].primary.model
        plan_route = ai.config.routes["plan"].primary.model
        logger.info(
            "chat runtime initialized. chat=%s, plan=%s, web_search=%s.",
            chat_route,
            plan_route,
            "enabled" if engine.web_configured else "disabled",
        )

        return cls(
            ai,
            engine,
            guards,
            max_output_tokens=config.CHAT_MAX_OUTPUT_TOKENS,
            owns_ai=owns_ai,
        )

    async def aclose(self) -> None:
        if self._owns_ai:
            await self._ai.aclose()


class ChatService:
    def __init__(self, runtime: ChatRuntime) -> None:
        self._runtime = runtime

    @property
    def runtime(self) -> ChatRuntime:
        return self._runtime

    async def prepare(self, request: Request, payload: ChatRequest) -> PreparedTurn:
        guards = self._runtime.guards
        guards.check_rate_limit(request)

        prompt_chars = len(payload.message) + sum(
            len(message.content) for message in payload.history
        )
        estimate = estimate_tokens(prompt_chars, self._runtime.max_output_tokens)
        reservation = guards.budget.reserve(estimate)

        try:
            await guards.concurrency.acquire()
        except BaseException:
            reservation.release()
            raise
        return PreparedTurn(
            message=payload.message,
            history=tuple(_history_turn(item) for item in payload.history),
            scope=_engine_scope(payload),
            reservation=reservation,
            guards=guards,
        )

    async def stream(self, turn: PreparedTurn, request: Request) -> AsyncIterator[str]:
        iterator = self._runtime.engine.stream(
            turn.message,
            history=turn.history,
            scope=turn.scope,
        )
        pending: asyncio.Task[EngineEvent] | None = None
        disconnect_task: asyncio.Task[None] = asyncio.create_task(
            _wait_disconnect(request)
        )
        generation_started = False
        terminal = False
        actual_tokens: int | None = None

        try:
            while True:
                if pending is None:
                    pending = asyncio.create_task(_next_event(iterator))
                done, _ = await asyncio.wait(
                    {pending, disconnect_task},
                    timeout=KEEPALIVE_SECONDS,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if disconnect_task in done:
                    logger.info("client disconnected. aborting chat stream.")
                    if pending is not None:
                        pending.cancel()
                        await asyncio.gather(pending, return_exceptions=True)
                        pending = None
                    break

                if not done:
                    yield KEEPALIVE_COMMENT
                    continue

                task, pending = pending, None
                try:
                    event = task.result()
                except StopAsyncIteration:
                    break

                if (
                    isinstance(event, StatusEvent)
                    and event.stage is ChatStage.GENERATING
                ):
                    generation_started = True
                if isinstance(event, DoneEvent):
                    terminal = True
                    actual_tokens = _usage_tokens(event.usage)
                elif isinstance(event, ErrorEvent):
                    terminal = True

                yield _sse_frame(event)

            if not terminal and not await request.is_disconnected():
                yield _sse_frame(
                    ErrorEvent(
                        code=ErrorCode.INTERNAL_ERROR,
                        message="The chat stream ended unexpectedly.",
                        retryable=True,
                    )
                )
        except Exception:
            logger.exception("chat stream failed.")
            yield _sse_frame(
                ErrorEvent(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="The chat stream failed unexpectedly.",
                    retryable=True,
                )
            )
        finally:
            disconnect_task.cancel()
            await asyncio.gather(disconnect_task, return_exceptions=True)
            try:
                if pending is not None:
                    pending.cancel()
                    await asyncio.gather(pending, return_exceptions=True)
                await _close_iterator(iterator)
            finally:
                if actual_tokens is not None:
                    turn.settle(actual_tokens)
                elif generation_started:
                    turn.settle(turn.reservation.tokens)
                else:
                    turn.settle(None)


def _history_turn(message: ChatHistoryMessage) -> ChatTurn:
    return ChatTurn(role=ChatRole(message.role), content=message.content)


def _engine_scope(payload: ChatRequest) -> ChatScope:
    scope = payload.scope
    if isinstance(scope, ChatEventScope):
        return ChatScope(type=ScopeType.EVENT, event_id=scope.event_id)
    if isinstance(scope, ChatViewportScope):
        return ChatScope(
            type=ScopeType.VIEWPORT,
            bbox=EngineBoundingBox(
                north=scope.bbox.north,
                south=scope.bbox.south,
                east=scope.bbox.east,
                west=scope.bbox.west,
            ),
        )
    return ChatScope(type=ScopeType.GLOBAL)


def _usage_tokens(usage: EngineUsage | None) -> int | None:
    if usage is None:
        return None
    return usage.total_tokens or None


def _sse_frame(event: EngineEvent) -> str:
    payload = _api_event(event)
    return f"event: {payload.type}\ndata: {payload.model_dump_json()}\n\n"


def _api_event(
    event: EngineEvent,
) -> (
    ChatStatusEvent | ChatTokenEvent | ChatSourcesEvent | ChatDoneEvent | ChatErrorEvent
):
    if isinstance(event, StatusEvent):
        return ChatStatusEvent(stage=event.stage.value)
    if isinstance(event, TokenEvent):
        return ChatTokenEvent(text=event.text)
    if isinstance(event, SourcesEvent):
        return ChatSourcesEvent(
            sources=[_api_source(source) for source in event.sources]
        )
    if isinstance(event, DoneEvent):
        usage = event.usage
        return ChatDoneEvent(
            provenance=ChatProvenance(
                events=event.provenance.events,
                articles=event.provenance.articles,
                timeline_nodes=event.provenance.timeline_nodes,
                web=event.provenance.web,
                background=event.provenance.background,
                grounding=[flag.value for flag in event.provenance.grounding],
            ),
            coverage=ChatCoverage(
                level=event.coverage.level.value,
                result_count=event.coverage.result_count,
                best_semantic_similarity=event.coverage.best_semantic_similarity,
                best_lexical_rank=event.coverage.best_lexical_rank,
                newest_age_hours=event.coverage.newest_age_hours,
                recency_stale=event.coverage.recency_stale,
            ),
            usage=(
                None
                if usage is None
                else ChatUsage(
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                )
            ),
            web_used=event.web_used,
            degraded=[flag.value for flag in event.degraded],
        )
    return ChatErrorEvent(
        code=event.code.value,
        message=event.message,
        retryable=event.retryable,
    )


def _api_source(source: EngineSource) -> ChatSource:
    return ChatSource(
        kind=source.kind.value,
        id=source.id,
        event_id=source.event_id,
        title=source.title,
        url=source.url,
        source_name=source.source_name,
        published_at=source.published_at,
        retrieved_at=source.retrieved_at,
        latitude=source.latitude,
        longitude=source.longitude,
        is_external=source.is_external,
        snippet=source.snippet,
    )


async def _close_iterator(iterator: AsyncIterator[EngineEvent]) -> None:
    aclose = getattr(iterator, "aclose", None)
    if not callable(aclose):
        return
    result = aclose()
    if inspect.isawaitable(result):
        await result


__all__ = ["ChatRuntime", "ChatService", "PreparedTurn"]
