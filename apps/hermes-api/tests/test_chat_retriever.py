"""Tests for the database-backed chat retrieval bridge."""

from __future__ import annotations
import asyncio
import uuid
from datetime import UTC, datetime, timedelta
import pytest
from hermes_ai.chat.models import (
    BoundingBox as ChatBoundingBox,
)
from hermes_ai.chat.models import (
    ChatScope,
    DegradedFlag,
    RetrievalFilters,
    ScopeType,
)
from hermes_ai.chat.models import (
    CoverageLevel as ChatCoverageLevel,
)
from hermes_db.enums import EventStatus, ImpactLevel
from hermes_db.services import (
    Coverage as SearchCoverage,
)
from hermes_db.services import (
    CoverageLevel as SearchCoverageLevel,
)
from hermes_db.services import (
    SearchArticle,
    SearchDegradedFlag,
    SearchEvent,
    SearchFilters,
    SearchResult,
    SearchScope,
    SearchTimeline,
    SearchTimelineEdge,
    SearchTimelineNode,
)
from hermes_api.services import chat_retriever
from hermes_api.services.chat_retriever import DbChatRetriever


NOW = datetime(2026, 11, 7, tzinfo=UTC)


class FakeEmbeddingClient:
    def __init__(
        self,
        embeddings: list[list[float] | None],
        *,
        error: Exception | None = None,
    ) -> None:
        self.embeddings = embeddings
        self.error = error
        self.calls: list[list[str]] = []

    async def gen_embeddings(self, texts: list[str]) -> list[list[float] | None]:
        self.calls.append(texts)
        if self.error is not None:
            raise self.error
        return self.embeddings


class FakeSession:
    def __init__(self) -> None:
        self.entered = False
        self.exited = False

    async def __aenter__(self) -> FakeSession:
        self.entered = True
        return self

    async def __aexit__(self, *args: object) -> bool:
        self.exited = True
        return False


class FakeSearchService:
    result: SearchResult
    captured_options: dict[str, object] = {}
    captured_retrieve: dict[str, object] = {}
    error: Exception | None = None

    def __init__(self, session: FakeSession, **options: object) -> None:
        self.session = session
        type(self).captured_options = options

    async def retrieve(self, query: str, **kwargs: object) -> SearchResult:
        type(self).captured_retrieve = {"query": query, **kwargs}
        if type(self).error is not None:
            raise type(self).error
        return type(self).result


@pytest.fixture(autouse=True)
def fake_search_service(monkeypatch: pytest.MonkeyPatch) -> type[FakeSearchService]:
    FakeSearchService.captured_options = {}
    FakeSearchService.captured_retrieve = {}
    FakeSearchService.error = None
    monkeypatch.setattr(chat_retriever, "SearchService", FakeSearchService)
    return FakeSearchService


def _event() -> SearchEvent:
    event_id = uuid.uuid4()
    return SearchEvent(
        id=event_id,
        ai_headline="Flooding in Valencia",
        ai_summary="Heavy rain flooded the city.",
        category="DISASTER",
        category_color="#ff8800",
        impact_level=ImpactLevel.MAJOR,
        status=EventStatus.ACTIVE,
        trending_score=0.7,
        last_updated_at=NOW,
        first_reported_at=NOW,
        location_name="Valencia, Spain",
        latitude=39.47,
        longitude=-0.37,
        lexical_rank=1,
        semantic_rank=None,
        semantic_similarity=None,
        rrf=0.016,
        age_hours=0.5,
        trending_norm=1.0,
        boost=1.2,
        score=0.019,
        articles=[
            SearchArticle(
                id=uuid.uuid4(),
                event_id=event_id,
                title="Flood report",
                url="https://example.com/flood",
                source_name="Example News",
                published_at=NOW,
            )
        ],
        timeline=SearchTimeline(
            summary="Timeline summary.",
            nodes=[
                SearchTimelineNode(
                    id="node-1",
                    date="2026-11-01",
                    headline="Storm forms",
                    summary="A storm formed.",
                    latitude=39.0,
                    longitude=-0.5,
                )
            ],
            edges=[
                SearchTimelineEdge(
                    source_node_id="node-1",
                    target_node_id="node-2",
                    relationship="led to",
                )
            ],
        ),
    )


def _result(
    *,
    events: list[SearchEvent] | None = None,
    level: SearchCoverageLevel = SearchCoverageLevel.SUFFICIENT,
    degraded: list[SearchDegradedFlag] | None = None,
) -> SearchResult:
    items = events or []
    return SearchResult(
        events=items,
        coverage=SearchCoverage(
            level=level,
            result_count=len(items),
            best_semantic_similarity=0.4 if items else None,
            best_lexical_rank=1 if items else None,
            newest_age_hours=0.5 if items else None,
        ),
        degraded=degraded or [],
    )


def _retriever(
    *,
    embeddings: list[list[float] | None],
    sessions: list[FakeSession],
    error: Exception | None = None,
) -> DbChatRetriever:
    def factory() -> FakeSession:
        session = FakeSession()
        sessions.append(session)
        return session

    return DbChatRetriever(
        FakeEmbeddingClient(embeddings, error=error),
        top_k=3,
        min_local_results=1,
        min_semantic_similarity=0.1,
        freshness_hours=12.0,
        session_factory=factory,
    )


def test_lexical_only_retrieval_maps_evidence_and_degradation(
    fake_search_service: type[FakeSearchService],
) -> None:
    fake_search_service.result = _result(
        events=[_event()],
        degraded=[SearchDegradedFlag.SEMANTIC_UNAVAILABLE],
    )
    sessions: list[FakeSession] = []
    retriever = _retriever(embeddings=[None], sessions=sessions)

    result = asyncio.run(
        retriever.retrieve("flooding", scope=ChatScope(type=ScopeType.GLOBAL))
    )

    assert fake_search_service.captured_retrieve["embedding"] is None
    assert fake_search_service.captured_retrieve["scope"] is SearchScope.GLOBAL
    assert fake_search_service.captured_options == {
        "top_k": 3,
        "min_local_results": 1,
        "min_semantic_similarity": 0.1,
        "freshness_hours": 12.0,
    }
    assert len(result.evidence) == 1
    evidence = result.evidence[0]
    assert evidence.headline == "Flooding in Valencia"
    assert evidence.impact_level == "MAJOR"
    assert evidence.status == "ACTIVE"
    assert evidence.location_name == "Valencia, Spain"
    assert evidence.articles[0].title == "Flood report"
    assert evidence.timeline is not None
    assert evidence.timeline.nodes[0].headline == "Storm forms"
    assert evidence.timeline.edges[0].relationship == "led to"
    assert result.coverage.level is ChatCoverageLevel.SUFFICIENT
    assert result.coverage.result_count == 1
    assert result.degraded == [DegradedFlag.SEMANTIC_UNAVAILABLE]
    assert sessions[0].entered is True
    assert sessions[0].exited is True


def test_selected_event_scope_passes_filters_and_embedding(
    fake_search_service: type[FakeSearchService],
) -> None:
    fake_search_service.result = _result(events=[_event()])
    event_id = uuid.uuid4()
    start = NOW - timedelta(days=1)
    sessions: list[FakeSession] = []
    retriever = _retriever(embeddings=[[0.4, 0.5]], sessions=sessions)

    result = asyncio.run(
        retriever.retrieve(
            "what happened",
            scope=ChatScope(type=ScopeType.EVENT, event_id=event_id),
            filters=RetrievalFilters(category="DISASTER", start=start, end=NOW),
            recency_intent=True,
        )
    )

    assert fake_search_service.captured_retrieve == {
        "query": "what happened",
        "scope": SearchScope.EVENT,
        "event_id": event_id,
        "bbox": None,
        "filters": SearchFilters(category="DISASTER", start=start, end=NOW),
        "embedding": [0.4, 0.5],
        "recency_intent": True,
    }
    assert len(result.evidence) == 1
    assert result.evidence[0].event_id == fake_search_service.result.events[0].id


def test_viewport_scope_maps_bounding_box(
    fake_search_service: type[FakeSearchService],
) -> None:
    fake_search_service.result = _result(events=[_event()])
    sessions: list[FakeSession] = []
    retriever = _retriever(embeddings=[None], sessions=sessions)

    asyncio.run(
        retriever.retrieve(
            "flooding",
            scope=ChatScope(
                type=ScopeType.VIEWPORT,
                bbox=ChatBoundingBox(north=51.0, south=40.0, east=10.0, west=-10.0),
            ),
        )
    )

    assert fake_search_service.captured_retrieve["scope"] is SearchScope.VIEWPORT
    bbox = fake_search_service.captured_retrieve["bbox"]
    assert bbox is not None
    assert bbox.north == 51.0
    assert bbox.south == 40.0
    assert bbox.east == 10.0
    assert bbox.west == -10.0


def test_embedding_failure_falls_back_to_lexical_search(
    fake_search_service: type[FakeSearchService],
) -> None:
    fake_search_service.result = _result(
        events=[_event()],
        degraded=[SearchDegradedFlag.SEMANTIC_UNAVAILABLE],
    )
    sessions: list[FakeSession] = []
    retriever = _retriever(
        embeddings=[None],
        sessions=sessions,
        error=RuntimeError("embedding provider unavailable"),
    )

    result = asyncio.run(
        retriever.retrieve("flooding", scope=ChatScope(type=ScopeType.GLOBAL))
    )

    assert fake_search_service.captured_retrieve["embedding"] is None
    assert result.degraded == [DegradedFlag.SEMANTIC_UNAVAILABLE]


def test_session_is_closed_when_search_fails(
    fake_search_service: type[FakeSearchService],
) -> None:
    fake_search_service.error = RuntimeError("database unavailable")
    sessions: list[FakeSession] = []
    retriever = _retriever(embeddings=[None], sessions=sessions)

    with pytest.raises(RuntimeError, match="database unavailable"):
        asyncio.run(
            retriever.retrieve("flooding", scope=ChatScope(type=ScopeType.GLOBAL))
        )

    assert sessions[0].entered is True
    assert sessions[0].exited is True
