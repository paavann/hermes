"""Tests for the streaming chat engine orchestration."""

import asyncio
import uuid
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime

import pytest
from langchain_core.messages import AIMessageChunk, BaseMessage, BaseMessageChunk

from hermes_ai.chat.engine import ChatEngine
from hermes_ai.chat.models import (
    ChatPlan,
    ChatScope,
    ChatSourceKind,
    ChatStage,
    ChatTurn,
    ChatUsage,
    Coverage,
    CoverageLevel,
    DegradedFlag,
    DoneEvent,
    EngineEvent,
    ErrorCode,
    ErrorEvent,
    GroundingFlag,
    RetrievalFilters,
    RetrievalResult,
    RetrievedArticle,
    RetrievedEvidence,
    RetrievedTimeline,
    RetrievedTimelineNode,
    ScopeType,
    SourcesEvent,
    StatusEvent,
    TokenEvent,
    WebResult,
)
from hermes_ai.chat.planner import PlannerOutcome
from hermes_ai.chat.web import WebSearchOutcome
from hermes_ai.core.config import AiConfig, ModelRoute, ModelTarget
from hermes_ai.services.llm import LlmService


NOW = datetime(2026, 11, 7, tzinfo=UTC)


def _config(*, tavily_api_key: str | None = None) -> AiConfig:
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
        },
        tavily_api_key=tavily_api_key,
    )


def _event(headline: str = "Flooding") -> RetrievedEvidence:
    event_id = uuid.uuid4()
    return RetrievedEvidence(
        event_id=event_id,
        headline=headline,
        summary="Summary.",
        category="DISASTER",
        impact_level="HIGH",
        status="ACTIVE",
        latitude=39.47,
        longitude=-0.37,
        first_reported_at=NOW,
        last_updated_at=NOW,
        articles=[
            RetrievedArticle(
                id=uuid.uuid4(),
                event_id=event_id,
                title="Report",
                url="https://example.com/report",
                source_name="Example",
                published_at=NOW,
            )
        ],
        timeline=RetrievedTimeline(
            summary="Timeline.",
            nodes=[
                RetrievedTimelineNode(
                    id="node-1",
                    date="2026-11-01",
                    headline="Rain",
                    summary="Storm.",
                )
            ],
        ),
    )


def _result(
    *,
    events: Sequence[RetrievedEvidence] = (),
    level: CoverageLevel = CoverageLevel.SUFFICIENT,
    degraded: Sequence[DegradedFlag] = (),
) -> RetrievalResult:
    coverage = Coverage(
        level=level,
        result_count=len(events),
        best_semantic_similarity=0.5 if events else None,
        best_lexical_rank=1 if events else None,
        newest_age_hours=1.0 if events else None,
    )
    return RetrievalResult(
        evidence=list(events),
        coverage=coverage,
        degraded=list(degraded),
    )


class FakePlanner:
    def __init__(self, plan: ChatPlan, *, degraded: bool = False) -> None:
        self._plan = plan
        self.degraded = degraded
        self.calls: list[tuple[str, Sequence[ChatTurn], ChatScope]] = []

    async def plan(
        self,
        message: str,
        *,
        history: Sequence[ChatTurn] = (),
        scope: ChatScope,
    ) -> PlannerOutcome:
        self.calls.append((message, history, scope))
        return PlannerOutcome(plan=self._plan, degraded=self.degraded)


class FakeRetriever:
    def __init__(self, result: RetrievalResult, *, delay_seconds: float = 0.0) -> None:
        self.result = result
        self.delay_seconds = delay_seconds
        self.calls: list[tuple[str, ChatScope, RetrievalFilters | None, bool]] = []

    async def retrieve(
        self,
        query: str,
        *,
        scope: ChatScope,
        filters: RetrievalFilters | None = None,
        recency_intent: bool = False,
    ) -> RetrievalResult:
        self.calls.append((query, scope, filters, recency_intent))
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        return self.result


class FakeWeb:
    def __init__(self, outcome: WebSearchOutcome) -> None:
        self.outcome = outcome
        self.calls: list[tuple[str, bool]] = []

    async def search(
        self, query: str, *, recency_intent: bool = False
    ) -> WebSearchOutcome:
        self.calls.append((query, recency_intent))
        return self.outcome


class FakeAnswer:
    def __init__(
        self,
        chunks: Sequence[AIMessageChunk],
        *,
        fail_after: int | None = None,
        delay_first: float = 0.0,
    ) -> None:
        self.chunks = chunks
        self.fail_after = fail_after
        self.delay_first = delay_first
        self.messages: list[Sequence[BaseMessage]] = []

    def astream(self, input: Sequence[BaseMessage]) -> AsyncIterator[BaseMessageChunk]:
        self.messages.append(input)

        async def generate() -> AsyncIterator[BaseMessageChunk]:
            if self.delay_first:
                await asyncio.sleep(self.delay_first)
            for index, chunk in enumerate(self.chunks):
                if self.fail_after is not None and index >= self.fail_after:
                    raise RuntimeError("model failed")
                yield chunk

        return generate()


def _engine(
    *,
    planner: FakePlanner,
    retriever: FakeRetriever,
    answer: FakeAnswer,
    web: FakeWeb | None = None,
    config: AiConfig | None = None,
    retrieval_timeout_seconds: float = 1.0,
    first_token_timeout_seconds: float = 1.0,
) -> ChatEngine:
    cfg = config or _config()
    return ChatEngine(
        LlmService(cfg),
        cfg,
        retriever=retriever,
        planner=planner,
        answer_model=answer,
        web_search=web,
        retrieval_timeout_seconds=retrieval_timeout_seconds,
        first_token_timeout_seconds=first_token_timeout_seconds,
    )


def _collect(
    engine: ChatEngine,
    *,
    message: str = "What happened?",
    scope: ChatScope | None = None,
) -> list[EngineEvent]:
    async def run() -> list[EngineEvent]:
        return [
            event
            async for event in engine.stream(
                message,
                scope=scope or ChatScope(type=ScopeType.GLOBAL),
            )
        ]

    return asyncio.run(run())


def _statuses(events: Sequence[EngineEvent]) -> list[ChatStage]:
    return [event.stage for event in events if isinstance(event, StatusEvent)]


def test_engine_orders_events_and_reports_provenance() -> None:
    plan = ChatPlan(query="flooding")
    answer = FakeAnswer(
        [
            AIMessageChunk(content="The [E1] flood "),
            AIMessageChunk(content="and [A1] report. "),
            AIMessageChunk(content="[T1][BG]"),
            AIMessageChunk(
                content="",
                usage_metadata={
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15,
                },
            ),
        ]
    )
    engine = _engine(
        planner=FakePlanner(plan),
        retriever=FakeRetriever(_result(events=[_event()])),
        answer=answer,
    )

    events = _collect(engine)

    assert _statuses(events) == [
        ChatStage.ACCEPTED,
        ChatStage.PLANNING,
        ChatStage.RETRIEVING,
        ChatStage.GENERATING,
        ChatStage.FINALIZING,
    ]
    tokens = "".join(event.text for event in events if isinstance(event, TokenEvent))
    assert tokens == "The [E1] flood and [A1] report. [T1][BG]"

    sources = next(event for event in events if isinstance(event, SourcesEvent))
    assert [source.kind for source in sources.sources] == [
        ChatSourceKind.EVENT,
        ChatSourceKind.ARTICLE,
        ChatSourceKind.TIMELINE,
    ]

    done = next(event for event in events if isinstance(event, DoneEvent))
    assert done.provenance.events == 1
    assert done.provenance.articles == 1
    assert done.provenance.timeline_nodes == 1
    assert done.provenance.web == 0
    assert done.provenance.background is True
    assert done.provenance.grounding == []
    assert done.web_used is False
    assert done.degraded == ()
    assert done.usage == ChatUsage(
        prompt_tokens=10, completion_tokens=5, total_tokens=15
    )
    assert done.coverage.level is CoverageLevel.SUFFICIENT


def test_no_web_search_when_coverage_is_sufficient() -> None:
    web = FakeWeb(
        WebSearchOutcome(
            results=[
                WebResult(
                    title="Web",
                    url="https://example.com",
                    retrieved_at=NOW,
                )
            ]
        )
    )
    engine = _engine(
        planner=FakePlanner(ChatPlan(query="flooding")),
        retriever=FakeRetriever(_result(events=[_event(), _event("Second")])),
        web=web,
        answer=FakeAnswer([AIMessageChunk(content="Answer [E1].")]),
        config=_config(tavily_api_key="key"),
    )

    events = _collect(engine)

    assert ChatStage.SEARCHING not in _statuses(events)
    assert web.calls == []
    done = next(event for event in events if isinstance(event, DoneEvent))
    assert done.web_used is False
    assert DegradedFlag.WEB_UNAVAILABLE not in done.degraded


def test_recency_intent_is_forwarded_and_stale_coverage_escalates() -> None:
    web = FakeWeb(WebSearchOutcome(results=[]))
    retriever = FakeRetriever(_result(events=[_event(), _event("Second")]))
    retriever.result.coverage.recency_stale = True
    engine = _engine(
        planner=FakePlanner(ChatPlan(query="latest", recency_intent=True)),
        retriever=retriever,
        web=web,
        answer=FakeAnswer([AIMessageChunk(content="[E1] Answer.")]),
        config=_config(tavily_api_key="key"),
    )

    events = _collect(engine)

    assert retriever.calls[0][3] is True
    assert ChatStage.SEARCHING in _statuses(events)


def test_empty_coverage_escalates_to_web() -> None:
    web = FakeWeb(
        WebSearchOutcome(
            results=[
                WebResult(
                    title="External report",
                    url="https://news.example.com/report",
                    source_name="news.example.com",
                    retrieved_at=NOW,
                    snippet="External details.",
                )
            ]
        )
    )
    engine = _engine(
        planner=FakePlanner(ChatPlan(query="latest", needs_web=True)),
        retriever=FakeRetriever(_result(level=CoverageLevel.EMPTY)),
        web=web,
        answer=FakeAnswer([AIMessageChunk(content="[BG] Context. [W1] External.")]),
        config=_config(tavily_api_key="key"),
    )

    events = _collect(engine)

    assert ChatStage.SEARCHING in _statuses(events)
    assert web.calls == [("latest", False)]
    done = next(event for event in events if isinstance(event, DoneEvent))
    assert done.web_used is True
    assert done.provenance.web == 1
    assert done.provenance.background is True
    sources = next(event for event in events if isinstance(event, SourcesEvent))
    assert sources.sources[0].kind is ChatSourceKind.WEB
    assert sources.sources[0].is_external is True


def test_web_failure_degrades_but_answers() -> None:
    web = FakeWeb(WebSearchOutcome(results=[], degraded=True, failure="timeout"))
    answer = FakeAnswer([AIMessageChunk(content="[BG] No data.")])
    engine = _engine(
        planner=FakePlanner(ChatPlan(query="latest")),
        retriever=FakeRetriever(_result(level=CoverageLevel.EMPTY)),
        web=web,
        answer=answer,
        config=_config(tavily_api_key="key"),
    )

    events = _collect(engine)

    done = next(event for event in events if isinstance(event, DoneEvent))
    assert DegradedFlag.WEB_UNAVAILABLE in done.degraded
    assert done.web_used is False
    assert any(isinstance(event, TokenEvent) for event in events)
    human = answer.messages[0][1].content
    assert '<web_evidence available="false">' in str(human)


def test_planner_fallback_is_reported_as_degraded() -> None:
    engine = _engine(
        planner=FakePlanner(ChatPlan(query="raw question"), degraded=True),
        retriever=FakeRetriever(_result(events=[_event()])),
        answer=FakeAnswer([AIMessageChunk(content="[E1] Grounded.")]),
    )

    done = next(event for event in _collect(engine) if isinstance(event, DoneEvent))

    assert DegradedFlag.PLANNER_FALLBACK in done.degraded


def test_semantic_unavailable_flag_is_propagated() -> None:
    engine = _engine(
        planner=FakePlanner(ChatPlan(query="flooding")),
        retriever=FakeRetriever(
            _result(
                events=[_event()],
                degraded=[DegradedFlag.SEMANTIC_UNAVAILABLE],
            )
        ),
        answer=FakeAnswer([AIMessageChunk(content="[E1] Grounded.")]),
    )

    done = next(event for event in _collect(engine) if isinstance(event, DoneEvent))

    assert DegradedFlag.SEMANTIC_UNAVAILABLE in done.degraded


def test_retrieval_timeout_is_terminal() -> None:
    engine = _engine(
        planner=FakePlanner(ChatPlan(query="flooding")),
        retriever=FakeRetriever(_result(events=[_event()]), delay_seconds=1.0),
        answer=FakeAnswer([]),
        retrieval_timeout_seconds=0.01,
    )

    events = _collect(engine)

    assert _statuses(events) == [
        ChatStage.ACCEPTED,
        ChatStage.PLANNING,
        ChatStage.RETRIEVING,
    ]
    error = events[-1]
    assert isinstance(error, ErrorEvent)
    assert error.code is ErrorCode.RETRIEVAL_FAILED
    assert error.retryable is True
    assert not any(isinstance(event, DoneEvent) for event in events)


def test_first_token_timeout_is_terminal() -> None:
    engine = _engine(
        planner=FakePlanner(ChatPlan(query="flooding")),
        retriever=FakeRetriever(_result(events=[_event()])),
        answer=FakeAnswer([AIMessageChunk(content="late")], delay_first=1.0),
        first_token_timeout_seconds=0.01,
    )

    events = _collect(engine)

    error = events[-1]
    assert isinstance(error, ErrorEvent)
    assert error.code is ErrorCode.MODEL_TIMEOUT
    assert not any(isinstance(event, DoneEvent) for event in events)


def test_model_failure_after_token_is_terminal() -> None:
    engine = _engine(
        planner=FakePlanner(ChatPlan(query="flooding")),
        retriever=FakeRetriever(_result(events=[_event()])),
        answer=FakeAnswer(
            [AIMessageChunk(content="[E1] first "), AIMessageChunk(content="x")],
            fail_after=1,
        ),
    )

    events = _collect(engine)

    error = events[-1]
    assert isinstance(error, ErrorEvent)
    assert error.code is ErrorCode.MODEL_FAILED
    assert any(isinstance(event, TokenEvent) for event in events)
    assert not any(isinstance(event, DoneEvent) for event in events)


def test_missing_citations_are_flagged() -> None:
    engine = _engine(
        planner=FakePlanner(ChatPlan(query="flooding")),
        retriever=FakeRetriever(_result(events=[_event()])),
        answer=FakeAnswer([AIMessageChunk(content="Unsupported answer.")]),
    )

    done = next(event for event in _collect(engine) if isinstance(event, DoneEvent))

    assert done.provenance.grounding == [GroundingFlag.MISSING_CITATIONS]
    assert done.provenance.background is False


def test_closing_stream_stops_without_error_or_done() -> None:
    engine = _engine(
        planner=FakePlanner(ChatPlan(query="flooding")),
        retriever=FakeRetriever(_result(events=[_event()])),
        answer=FakeAnswer([AIMessageChunk(content="[E1] answer")]),
    )

    async def run() -> list[EngineEvent]:
        events: list[EngineEvent] = []
        stream = engine.stream(
            "What happened?",
            scope=ChatScope(type=ScopeType.GLOBAL),
        )
        async for event in stream:
            events.append(event)
            if isinstance(event, StatusEvent) and event.stage is ChatStage.ACCEPTED:
                await stream.aclose()
                break
        return events

    events = asyncio.run(run())

    assert _statuses(events) == [ChatStage.ACCEPTED]
    assert not any(isinstance(event, ErrorEvent | DoneEvent) for event in events)


def test_missing_retriever_raises_type_error() -> None:
    cfg = _config()
    with pytest.raises(TypeError, match="retriever"):
        ChatEngine(  # type: ignore[call-arg]
            LlmService(cfg),
            cfg,
            planner=FakePlanner(ChatPlan(query="flooding")),
            answer_model=FakeAnswer([]),
        )
