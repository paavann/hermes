"""Unit tests for hybrid search query construction, ranking, and context loading."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import ExecutableReturnsRows

from hermes_db.enums import EventStatus, ImpactLevel
from hermes_db.services.search import (
    MAX_QUERY_CHARS,
    BoundingBox,
    CoverageLevel,
    SearchDegradedFlag,
    SearchEvent,
    SearchFilters,
    SearchScope,
    SearchService,
    boost_multiplier,
    classify_coverage,
    reciprocal_rank_fusion,
)


NOW = datetime(2026, 11, 7, 12, 0, 0, tzinfo=UTC)
CUTOFF = NOW - timedelta(days=7)


class _Mappings:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def all(self) -> list[dict[str, object]]:
        return self._rows

    def first(self) -> dict[str, object] | None:
        return self._rows[0] if self._rows else None


class _Result:
    def __init__(
        self,
        *,
        mapping_rows: list[dict[str, object]] | None = None,
        first: tuple[object, ...] | None = None,
        all_rows: list[tuple[object, ...]] | None = None,
    ) -> None:
        self._mapping_rows = mapping_rows or []
        self._first = first
        self._all_rows = all_rows or []

    def mappings(self) -> _Mappings:
        return _Mappings(self._mapping_rows)

    def first(self) -> tuple[object, ...] | None:
        return self._first

    def all(self) -> list[tuple[object, ...]]:
        return self._all_rows


class _Session:
    def __init__(self, results: list[_Result]) -> None:
        self._results = list(results)
        self.statements: list[ExecutableReturnsRows] = []

    async def execute(self, stmt: ExecutableReturnsRows) -> _Result:
        self.statements.append(stmt)
        return self._results.pop(0)


def _service(results: list[_Result] | None = None) -> tuple[SearchService, _Session]:
    session = _Session(results or [])
    return SearchService(cast(AsyncSession, session)), session


def _sql(stmt: ExecutableReturnsRows) -> str:
    return str(
        stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


def _build(
    svc: SearchService,
    *,
    embedding: list[float] | None = None,
    scope: SearchScope = SearchScope.GLOBAL,
    bbox: BoundingBox | None = None,
    filters: SearchFilters | None = None,
    query: str = "ceasefire talks",
) -> str:
    return _sql(
        svc._build_statement(
            query=query,
            embedding=embedding,
            scope=scope,
            bbox=bbox,
            filters=filters,
            now=NOW,
            cutoff=CUTOFF,
        )
    )


def _search_event(
    *,
    event_id: uuid.UUID | None = None,
    lexical_rank: int | None = 1,
    semantic_rank: int | None = 1,
    semantic_similarity: float | None = 0.40,
    age_hours: float = 2.0,
) -> SearchEvent:
    return SearchEvent(
        id=event_id or uuid.uuid4(),
        ai_headline="Ceasefire talks resume",
        ai_summary="Talks resumed in the capital.",
        category="POLITICS",
        category_color="#3B82F6",
        impact_level=ImpactLevel.MAJOR,
        status=EventStatus.ACTIVE,
        trending_score=8.0,
        last_updated_at=NOW - timedelta(hours=age_hours),
        first_reported_at=NOW - timedelta(days=1),
        location_name="Geneva, Switzerland",
        latitude=46.2,
        longitude=6.1,
        lexical_rank=lexical_rank,
        semantic_rank=semantic_rank,
        semantic_similarity=semantic_similarity,
        rrf=0.025,
        age_hours=age_hours,
    )


def _event_row(
    *,
    event_id: uuid.UUID,
    headline: str = "Ceasefire talks resume",
    lexical_rank: int | None = 1,
    semantic_rank: int | None = 1,
    semantic_similarity: float | None = 0.42,
    age_hours: float = 3.0,
    trending_score: float = 8.0,
    trending_norm: float = 0.8,
    boost: float = 1.2,
    score: float = 0.03,
) -> dict[str, object]:
    return {
        "id": event_id,
        "ai_headline": headline,
        "ai_summary": "Talks resumed in the capital.",
        "category": "POLITICS",
        "category_color": "#3B82F6",
        "impact_level": ImpactLevel.MAJOR,
        "status": EventStatus.ACTIVE,
        "trending_score": trending_score,
        "last_updated_at": NOW - timedelta(hours=age_hours),
        "first_reported_at": NOW - timedelta(days=1),
        "location_name": "Geneva, Switzerland",
        "latitude": 46.2,
        "longitude": 6.1,
        "lexical_rank": lexical_rank,
        "semantic_rank": semantic_rank,
        "semantic_similarity": semantic_similarity,
        "rrf": 0.025,
        "age_hours": age_hours,
        "trending_norm": trending_norm,
        "boost": boost,
        "score": score,
    }


def test_global_scope_has_eligibility_without_spatial_predicate() -> None:
    svc, _ = _service()
    sql = _build(svc)

    assert "ST_Within" not in sql
    assert "events.status IN ('ACTIVE', 'STALE')" in sql
    assert "events.last_updated_at >=" in sql


def test_viewport_scope_uses_one_envelope() -> None:
    svc, _ = _service()
    sql = _build(
        svc,
        scope=SearchScope.VIEWPORT,
        bbox=BoundingBox(north=60.0, south=30.0, east=60.0, west=20.0),
    )

    assert sql.count("ST_Within") == 1
    assert "ST_MakeEnvelope(20.0, 30.0, 60.0, 60.0, 4326)" in sql


def test_antimeridian_viewport_splits_into_two_envelopes() -> None:
    svc, _ = _service()
    sql = _build(
        svc,
        scope=SearchScope.VIEWPORT,
        bbox=BoundingBox(north=10.0, south=-10.0, east=-170.0, west=170.0),
    )

    assert sql.count("ST_Within") == 2
    assert "ST_MakeEnvelope(170.0, -10.0, 180.0, 10.0, 4326)" in sql
    assert "ST_MakeEnvelope(-180.0, -10.0, -170.0, 10.0, 4326)" in sql
    assert " OR " in sql


def test_filters_apply_before_ranking_and_keep_eligibility() -> None:
    svc, _ = _service()
    sql = _build(
        svc,
        filters=SearchFilters(
            category="politics",
            start=NOW - timedelta(days=30),
            end=NOW + timedelta(days=1),
        ),
    )

    assert "upper(events.category) = 'POLITICS'" in sql
    assert "events.first_reported_at <=" in sql
    assert "events.status IN ('ACTIVE', 'STALE')" in sql
    assert "events.last_updated_at >=" in sql


def test_archived_and_out_of_window_events_are_filtered_by_base_predicates() -> None:
    svc, _ = _service()
    sql = _build(svc, filters=SearchFilters(category="POLITICS"))

    assert "ARCHIVED" not in sql
    assert "events.status IN ('ACTIVE', 'STALE')" in sql
    assert "events.last_updated_at >=" in sql


def test_hybrid_statement_uses_full_outer_join_and_vector_distance() -> None:
    svc, _ = _service()
    sql = _build(svc, embedding=[0.1] * 8)

    assert "FULL OUTER JOIN" in sql
    assert "<=>" in sql
    assert "60 +" in sql


def test_selected_event_scope_queries_eligibility() -> None:
    event_id = uuid.uuid4()
    session = _Session([_Result(first=None)])
    svc = SearchService(cast(AsyncSession, session))

    result = asyncio.run(
        svc.retrieve(
            "selected event",
            scope=SearchScope.EVENT,
            event_id=event_id,
        )
    )

    assert result.events == []
    assert result.coverage.level is CoverageLevel.EMPTY
    assert len(session.statements) == 1
    sql = _sql(session.statements[0])
    assert "events.id =" in sql
    assert "events.status IN ('ACTIVE', 'STALE')" in sql


def test_empty_retrieval_reports_semantic_unavailable() -> None:
    session = _Session([_Result(mapping_rows=[]), _Result(mapping_rows=[])])
    svc = SearchService(cast(AsyncSession, session))

    result = asyncio.run(svc.retrieve("no matches", embedding=None))

    assert len(session.statements) == 2
    assert "<=>" not in _sql(session.statements[0])
    assert " or " in _sql(session.statements[1])
    assert result.coverage.level is CoverageLevel.EMPTY
    assert result.degraded == [SearchDegradedFlag.SEMANTIC_UNAVAILABLE]


def test_empty_strict_query_retries_with_relaxed_terms() -> None:
    event_id = uuid.uuid4()
    session = _Session(
        [
            _Result(mapping_rows=[]),
            _Result(mapping_rows=[_event_row(event_id=event_id)]),
            _Result(all_rows=[]),
            _Result(all_rows=[]),
        ]
    )
    svc = SearchService(cast(AsyncSession, session))

    result = asyncio.run(
        svc.retrieve("recent bomb threats incidents across Europe", embedding=None)
    )

    assert len(session.statements) == 4
    assert "bomb or threats" in _sql(session.statements[1])
    assert [event.id for event in result.events] == [event_id]
    assert result.coverage.level is CoverageLevel.THIN


def test_retrieval_maps_signals_and_loads_context() -> None:
    event_id = uuid.uuid4()
    session = _Session(
        [
            _Result(mapping_rows=[_event_row(event_id=event_id)]),
            _Result(all_rows=[]),
            _Result(all_rows=[]),
        ]
    )
    svc = SearchService(cast(AsyncSession, session))

    result = asyncio.run(svc.retrieve("ceasefire", embedding=[0.1] * 8))

    assert len(result.events) == 1
    event = result.events[0]
    assert event.id == event_id
    assert event.lexical_rank == 1
    assert event.semantic_similarity == 0.42
    assert event.age_hours == 3.0
    assert event.articles == []
    assert event.timeline is None
    assert result.coverage.level is CoverageLevel.THIN
    assert result.degraded == []


def test_query_is_capped_before_binding() -> None:
    session = _Session([_Result(mapping_rows=[])])
    svc = SearchService(cast(AsyncSession, session))

    asyncio.run(svc.retrieve("a" * (MAX_QUERY_CHARS + 100)))

    sql = _sql(session.statements[0])
    assert "a" * MAX_QUERY_CHARS in sql
    assert "a" * (MAX_QUERY_CHARS + 1) not in sql


def test_reciprocal_rank_fusion_prefers_agreement() -> None:
    agreement = reciprocal_rank_fusion(1, 1)

    assert agreement > reciprocal_rank_fusion(1, None)
    assert agreement > reciprocal_rank_fusion(None, 2)
    assert reciprocal_rank_fusion(None, None) == 0.0


def test_boost_is_bounded_and_never_overrides_strong_relevance() -> None:
    assert boost_multiplier(0.0, 10.0, 10.0) == 1.25
    assert boost_multiplier(10_000.0, 0.0, 10.0) == 1.0

    strong = reciprocal_rank_fusion(1, 1)
    weak = reciprocal_rank_fusion(2, None) * boost_multiplier(0.0, 10.0, 10.0)

    assert weak < strong


def test_coverage_empty_thin_and_sufficient() -> None:
    empty = classify_coverage(
        [],
        min_local_results=2,
        min_semantic_similarity=0.2,
        freshness_hours=24.0,
        recency_intent=False,
    )
    thin = classify_coverage(
        [_search_event(semantic_similarity=0.9)],
        min_local_results=2,
        min_semantic_similarity=0.2,
        freshness_hours=24.0,
        recency_intent=False,
    )
    sufficient = classify_coverage(
        [_search_event(), _search_event(event_id=uuid.uuid4())],
        min_local_results=2,
        min_semantic_similarity=0.2,
        freshness_hours=24.0,
        recency_intent=False,
    )

    assert empty.level is CoverageLevel.EMPTY
    assert thin.level is CoverageLevel.THIN
    assert sufficient.level is CoverageLevel.SUFFICIENT


def test_coverage_accepts_top_lexical_rank_without_semantics() -> None:
    coverage = classify_coverage(
        [
            _search_event(semantic_similarity=None, lexical_rank=2),
            _search_event(
                event_id=uuid.uuid4(),
                semantic_similarity=None,
                lexical_rank=9,
            ),
        ],
        min_local_results=2,
        min_semantic_similarity=0.2,
        freshness_hours=24.0,
        recency_intent=False,
    )

    assert coverage.level is CoverageLevel.SUFFICIENT
    assert coverage.best_lexical_rank == 2


def test_recency_intent_downgrades_stale_evidence_to_thin() -> None:
    coverage = classify_coverage(
        [
            _search_event(age_hours=48.0),
            _search_event(event_id=uuid.uuid4(), age_hours=50.0),
        ],
        min_local_results=2,
        min_semantic_similarity=0.2,
        freshness_hours=24.0,
        recency_intent=True,
    )

    assert coverage.level is CoverageLevel.THIN
    assert coverage.recency_stale is True


def test_article_loader_groups_and_caps_per_event() -> None:
    event_a = uuid.uuid4()
    event_b = uuid.uuid4()
    session = _Session(
        [
            _Result(
                all_rows=[
                    (
                        uuid.uuid4(),
                        event_a,
                        "A1",
                        "https://example.com/a1",
                        NOW,
                        "Wire",
                    ),
                    (
                        uuid.uuid4(),
                        event_a,
                        "A2",
                        "https://example.com/a2",
                        None,
                        "Paper",
                    ),
                    (
                        uuid.uuid4(),
                        event_b,
                        "B1",
                        "https://example.com/b1",
                        NOW,
                        None,
                    ),
                ]
            )
        ]
    )
    svc = SearchService(cast(AsyncSession, session))

    grouped = asyncio.run(svc._load_articles([event_a, event_b]))

    assert [article.title for article in grouped[event_a]] == ["A1", "A2"]
    assert grouped[event_b][0].source_name is None
    assert grouped[event_b][0].published_at == NOW
    assert "rank <= 5" in _sql(session.statements[0])


def test_timeline_loader_parses_nodes_edges_and_null_coordinates() -> None:
    event_id = uuid.uuid4()
    session = _Session(
        [
            _Result(
                all_rows=[
                    (
                        event_id,
                        [
                            {
                                "id": "n1",
                                "date": "2024-01-01",
                                "headline": "First",
                                "summary": "First node",
                                "location_name": None,
                                "latitude": None,
                                "longitude": None,
                            }
                        ],
                        [
                            {
                                "source_node_id": "n1",
                                "target_node_id": "current-event",
                                "relationship": "led to",
                            }
                        ],
                        "Historical arc",
                    )
                ]
            )
        ]
    )
    svc = SearchService(cast(AsyncSession, session))

    timelines = asyncio.run(svc._load_timelines([event_id]))

    timeline = timelines[event_id]
    assert timeline.summary == "Historical arc"
    assert timeline.nodes[0].latitude is None
    assert timeline.edges[0].relationship == "led to"


def test_context_loader_leaves_missing_timeline_empty() -> None:
    event = _search_event()
    session = _Session([_Result(all_rows=[]), _Result(all_rows=[])])
    svc = SearchService(cast(AsyncSession, session))

    asyncio.run(svc._load_context([event]))

    assert event.articles == []
    assert event.timeline is None


def test_selected_event_scope_projects_columns_and_loads_context() -> None:
    event_id = uuid.uuid4()
    row = _event_row(event_id=event_id)
    for key in (
        "lexical_rank",
        "semantic_rank",
        "semantic_similarity",
        "rrf",
        "trending_norm",
        "boost",
        "score",
    ):
        row.pop(key)
    session = _Session(
        [
            _Result(mapping_rows=[row]),
            _Result(all_rows=[]),
            _Result(all_rows=[]),
        ]
    )
    svc = SearchService(cast(AsyncSession, session))

    result = asyncio.run(
        svc.retrieve(
            "selected event",
            scope=SearchScope.EVENT,
            event_id=event_id,
        )
    )

    assert len(session.statements) == 3
    sql = _sql(session.statements[0])
    assert "events.embedding" not in sql
    assert [event.id for event in result.events] == [event_id]
    assert result.events[0].boost == 1.0
    assert result.coverage.level is CoverageLevel.THIN


def test_search_event_model_validate_normalizes_utc_and_rejects_booleans() -> None:
    event_id = uuid.uuid4()
    row = _event_row(event_id=event_id)
    row["last_updated_at"] = NOW.replace(tzinfo=None)
    row["first_reported_at"] = NOW.replace(tzinfo=None)

    parsed = SearchEvent.model_validate(row)
    assert parsed.last_updated_at == NOW
    assert parsed.first_reported_at == NOW

    bad_float_row = {**row, "trending_score": True}
    with pytest.raises(ValidationError):
        SearchEvent.model_validate(bad_float_row)

    bad_int_row = {**row, "lexical_rank": False}
    with pytest.raises(ValidationError):
        SearchEvent.model_validate(bad_int_row)
