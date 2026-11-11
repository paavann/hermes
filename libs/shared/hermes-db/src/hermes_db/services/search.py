from __future__ import annotations

import enum
import math
import uuid
import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Self

from geoalchemy2.functions import ST_X, ST_Y, ST_MakeEnvelope, ST_Within
from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy import (
    Float,
    Integer,
    Select,
    cast,
    func,
    literal,
    literal_column,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from hermes_db.enums import EventStatus, EventTlStatus, ImpactLevel
from hermes_db.models.article import Article
from hermes_db.models.event import Event, event_fts_expression
from hermes_db.models.event_tl import EventTl
from hermes_db.models.source import Source


logger = logging.getLogger(__name__)

RRF_K = 60
RECENCY_WEIGHT = 0.15
TRENDING_WEIGHT = 0.10
RECENCY_WINDOW_HOURS = 168.0
MAX_QUERY_CHARS = 400

REG_CONFIG = literal_column("'english'::regconfig")


class SearchScope(enum.StrEnum):
    EVENT = "event"
    VIEWPORT = "viewport"
    GLOBAL = "global"


class CoverageLevel(enum.StrEnum):
    EMPTY = "empty"
    THIN = "thin"
    SUFFICIENT = "sufficient"


class SearchDegradedFlag(enum.StrEnum):
    SEMANTIC_UNAVAILABLE = "semantic_unavailable"


class BoundingBox(BaseModel):
    north: float
    south: float
    east: float
    west: float

    @model_validator(mode="after")
    def _validate_bounds(self) -> Self:
        if self.north < self.south:
            raise ValueError("north must be greater than or equal to south.")
        if not -90.0 <= self.south <= 90.0 or not -90.0 <= self.north <= 90.0:
            raise ValueError("latitudes must be within [-90, 90].")
        if not -180.0 <= self.west <= 180.0 or not -180.0 <= self.east <= 180.0:
            raise ValueError("longitudes must be within [-180, 180].")
        return self


class SearchFilters(BaseModel):
    category: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    @model_validator(mode="after")
    def _validate_range(self) -> Self:
        if self.start and self.end and self.start > self.end:
            raise ValueError("start must be before or equal to end.")
        return self


class SearchArticle(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    title: str
    url: str
    source_name: str | None = None
    published_at: datetime | None = None


class SearchTimelineNode(BaseModel):
    id: str
    date: str
    headline: str
    summary: str
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    category_color: str | None = None


class SearchTimelineEdge(BaseModel):
    source_node_id: str
    target_node_id: str
    relationship: str


class SearchTimeline(BaseModel):
    summary: str = ""
    nodes: list[SearchTimelineNode] = Field(default_factory=list)
    edges: list[SearchTimelineEdge] = Field(default_factory=list)


class SearchEvent(BaseModel):
    id: uuid.UUID
    ai_headline: str
    ai_summary: str | None = None
    category: str
    category_color: str
    impact_level: ImpactLevel
    status: EventStatus
    trending_score: float
    last_updated_at: datetime
    first_reported_at: datetime
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    lexical_rank: int | None = None
    semantic_rank: int | None = None
    semantic_similarity: float | None = None
    rrf: float = 0.0
    age_hours: float = 0.0
    trending_norm: float = 0.0
    boost: float = 1.0
    score: float = 0.0
    articles: list[SearchArticle] = Field(default_factory=list)
    timeline: SearchTimeline | None = None


class Coverage(BaseModel):
    level: CoverageLevel
    result_count: int
    best_semantic_similarity: float | None = None
    best_lexical_rank: int | None = None
    newest_age_hours: float | None = None
    recency_stale: bool = False


class SearchResult(BaseModel):
    events: list[SearchEvent] = Field(default_factory=list)
    coverage: Coverage
    degraded: list[SearchDegradedFlag] = Field(default_factory=list)


def reciprocal_rank_fusion(
    lexical_rank: int | None,
    semantic_rank: int | None,
    *,
    k: int = RRF_K,
) -> float:
    score = 0.0
    if lexical_rank is not None:
        score += 1.0 / (k + lexical_rank)
    if semantic_rank is not None:
        score += 1.0 / (k + semantic_rank)
    return score


def boost_multiplier(
    age_hours: float,
    trending_score: float,
    max_trending_score: float,
) -> float:
    recency = math.exp(-max(age_hours, 0.0) / RECENCY_WINDOW_HOURS)
    trending_norm = (
        min(1.0, trending_score / max_trending_score)
        if max_trending_score > 0
        else 0.0
    )
    return 1.0 + RECENCY_WEIGHT * recency + TRENDING_WEIGHT * trending_norm


def classify_coverage(
    events: Sequence[SearchEvent],
    *,
    min_local_results: int,
    min_semantic_similarity: float,
    freshness_hours: float,
    recency_intent: bool,
) -> Coverage:
    count = len(events)
    semantics = [
        event.semantic_similarity
        for event in events
        if event.semantic_similarity is not None
    ]
    lexical = [
        event.lexical_rank for event in events if event.lexical_rank is not None
    ]
    ages = [event.age_hours for event in events]

    best_semantic = max(semantics) if semantics else None
    best_lexical = min(lexical) if lexical else None
    newest_age = min(ages) if ages else None
    recency_stale = (
        recency_intent
        and newest_age is not None
        and newest_age > freshness_hours
    )

    strong = (
        count >= min_local_results
        and (
            (best_semantic is not None and best_semantic >= min_semantic_similarity)
            or (best_lexical is not None and best_lexical <= 3)
        )
    )
    if count == 0:
        level = CoverageLevel.EMPTY
    elif strong and not recency_stale:
        level = CoverageLevel.SUFFICIENT
    else:
        level = CoverageLevel.THIN

    return Coverage(
        level=level,
        result_count=count,
        best_semantic_similarity=best_semantic,
        best_lexical_rank=best_lexical,
        newest_age_hours=newest_age,
        recency_stale=recency_stale,
    )


def _relaxed_query(query: str) -> str | None:
    """Join query terms with OR so verbose planner rewrites still match."""
    terms = [
        term.strip('"')
        for term in query.split()
        if term.strip('"') and term.casefold() not in {"and", "or", "not"}
    ]
    if len(terms) < 2:
        return None
    return " or ".join(terms)[:MAX_QUERY_CHARS]


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _as_float(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("expected a numeric value.")
    if isinstance(value, int | float | Decimal):
        return float(value)
    if isinstance(value, str):
        return float(value)
    raise ValueError("expected a numeric value.")


def _as_optional_float(value: object) -> float | None:
    return None if value is None else _as_float(value)


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("expected an integer value.")
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise ValueError("expected an integer value.")


def _as_optional_int(value: object) -> int | None:
    return None if value is None else _as_int(value)


def _as_datetime(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError("expected a datetime value.")
    return value


class SearchService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        top_k: int = 8,
        lexical_limit: int = 40,
        semantic_limit: int = 40,
        min_local_results: int = 2,
        min_semantic_similarity: float = 0.20,
        freshness_hours: float = 24.0,
        lookback_days: int = 7,
        articles_per_event: int = 5,
        rrf_k: int = RRF_K,
    ) -> None:
        if top_k < 1:
            raise ValueError("top_k must be positive.")
        self._session = session
        self._top_k = top_k
        self._lexical_limit = lexical_limit
        self._semantic_limit = semantic_limit
        self._min_local_results = min_local_results
        self._min_semantic_similarity = min_semantic_similarity
        self._freshness_hours = freshness_hours
        self._lookback_days = lookback_days
        self._articles_per_event = articles_per_event
        self._rrf_k = rrf_k

    async def retrieve(
        self,
        query: str,
        *,
        scope: SearchScope = SearchScope.GLOBAL,
        event_id: uuid.UUID | None = None,
        bbox: BoundingBox | None = None,
        filters: SearchFilters | None = None,
        embedding: Sequence[float] | None = None,
        recency_intent: bool = False,
    ) -> SearchResult:
        query = query.strip()
        if not query:
            raise ValueError("query must not be empty.")
        query = query[:MAX_QUERY_CHARS]
        self._validate_scope(scope=scope, event_id=event_id, bbox=bbox)

        now = datetime.now(UTC).replace(tzinfo=None)
        cutoff = now - timedelta(days=self._lookback_days)

        if scope is SearchScope.EVENT:
            return await self._retrieve_selected_event(
                event_id=event_id,
                now=now,
                cutoff=cutoff,
                recency_intent=recency_intent,
            )

        stmt = self._build_statement(
            query=query,
            embedding=embedding,
            scope=scope,
            bbox=bbox,
            filters=filters,
            now=now,
            cutoff=cutoff,
        )
        result = await self._session.execute(stmt)
        rows = result.mappings().all()
        if not rows:
            relaxed = _relaxed_query(query)
            if relaxed is not None:
                logger.debug(
                    "strict retrieval matched no events; retrying with OR terms."
                )
                stmt = self._build_statement(
                    query=relaxed,
                    embedding=embedding,
                    scope=scope,
                    bbox=bbox,
                    filters=filters,
                    now=now,
                    cutoff=cutoff,
                )
                result = await self._session.execute(stmt)
                rows = result.mappings().all()
        events = [self._event_from_row(row) for row in rows]
        await self._load_context(events)

        degraded: list[SearchDegradedFlag] = []
        if not embedding:
            degraded.append(SearchDegradedFlag.SEMANTIC_UNAVAILABLE)

        return SearchResult(
            events=events,
            coverage=classify_coverage(
                events,
                min_local_results=self._min_local_results,
                min_semantic_similarity=self._min_semantic_similarity,
                freshness_hours=self._freshness_hours,
                recency_intent=recency_intent,
            ),
            degraded=degraded,
        )

    async def _retrieve_selected_event(
        self,
        *,
        event_id: uuid.UUID | None,
        now: datetime,
        cutoff: datetime,
        recency_intent: bool,
    ) -> SearchResult:
        if event_id is None:
            raise ValueError("event scope requires event_id.")
        stmt = (
            select(Event, ST_Y(Event.location), ST_X(Event.location))
            .where(Event.id == event_id)
            .where(Event.status.in_([EventStatus.ACTIVE, EventStatus.STALE]))
            .where(Event.last_updated_at >= cutoff)
        )
        result = await self._session.execute(stmt)
        row = result.first()
        if row is None:
            return SearchResult(
                events=[],
                coverage=classify_coverage(
                    [],
                    min_local_results=self._min_local_results,
                    min_semantic_similarity=self._min_semantic_similarity,
                    freshness_hours=self._freshness_hours,
                    recency_intent=recency_intent,
                ),
            )

        event, latitude, longitude = row
        age_hours = max(
            0.0, (now - _as_datetime(event.last_updated_at)).total_seconds() / 3600.0
        )
        search_event = SearchEvent(
            id=event.id,
            ai_headline=event.ai_headline,
            ai_summary=event.ai_summary,
            category=event.category,
            category_color=event.category_color,
            impact_level=ImpactLevel(event.impact_level),
            status=EventStatus(event.status),
            trending_score=float(event.trending_score),
            last_updated_at=_as_datetime(event.last_updated_at),
            first_reported_at=_as_datetime(event.first_reported_at),
            location_name=event.location_name,
            latitude=_as_optional_float(latitude),
            longitude=_as_optional_float(longitude),
            age_hours=age_hours,
            boost=boost_multiplier(
                age_hours,
                float(event.trending_score),
                max(float(event.trending_score), 1.0),
            ),
        )
        await self._load_context([search_event])
        return SearchResult(
            events=[search_event],
            coverage=classify_coverage(
                [search_event],
                min_local_results=self._min_local_results,
                min_semantic_similarity=self._min_semantic_similarity,
                freshness_hours=self._freshness_hours,
                recency_intent=recency_intent,
            ),
        )

    def _validate_scope(
        self,
        *,
        scope: SearchScope,
        event_id: uuid.UUID | None,
        bbox: BoundingBox | None,
    ) -> None:
        if scope is SearchScope.EVENT and event_id is None:
            raise ValueError("event scope requires event_id.")
        if scope is SearchScope.VIEWPORT and bbox is None:
            raise ValueError("viewport scope requires bbox.")

    def _build_statement(
        self,
        *,
        query: str,
        embedding: Sequence[float] | None,
        scope: SearchScope,
        bbox: BoundingBox | None,
        filters: SearchFilters | None,
        now: datetime,
        cutoff: datetime,
    ) -> Select[tuple[object, ...]]:
        conditions = self._eligibility_conditions(
            scope=scope,
            bbox=bbox,
            filters=filters,
            now=now,
            cutoff=cutoff,
        )
        fts = event_fts_expression(
            Event.ai_headline,
            Event.ai_summary,
            Event.location_name,
            Event.category,
        )
        ts_query = func.websearch_to_tsquery(REG_CONFIG, query)

        lexical = (
            select(
                Event.id.label("id"),
                func.row_number()
                .over(order_by=func.ts_rank_cd(fts, ts_query).desc())
                .label("rank"),
            )
            .where(*conditions)
            .where(fts.op("@@")(ts_query))
            .order_by(func.ts_rank_cd(fts, ts_query).desc())
            .limit(self._lexical_limit)
            .cte("lexical")
        )

        if embedding:
            distance = Event.embedding.cosine_distance(list(embedding))
            semantic = (
                select(
                    Event.id.label("id"),
                    func.row_number().over(order_by=distance).label("rank"),
                    distance.label("distance"),
                )
                .where(*conditions)
                .where(Event.embedding.is_not(None))
                .order_by(distance)
                .limit(self._semantic_limit)
                .cte("semantic")
            )
            fused = (
                select(
                    func.coalesce(lexical.c.id, semantic.c.id).label("id"),
                    lexical.c.rank.label("lexical_rank"),
                    semantic.c.rank.label("semantic_rank"),
                    (1.0 - semantic.c.distance).label("semantic_similarity"),
                    (
                        func.coalesce(1.0 / (self._rrf_k + lexical.c.rank), 0.0)
                        + func.coalesce(1.0 / (self._rrf_k + semantic.c.rank), 0.0)
                    ).label("rrf"),
                )
                .select_from(
                    lexical.join(
                        semantic, lexical.c.id == semantic.c.id, full=True
                    )
                )
                .cte("fused")
            )
        else:
            fused = (
                select(
                    lexical.c.id.label("id"),
                    lexical.c.rank.label("lexical_rank"),
                    cast(literal(None), Integer).label("semantic_rank"),
                    cast(literal(None), Float).label("semantic_similarity"),
                    (1.0 / (self._rrf_k + lexical.c.rank)).label("rrf"),
                )
                .cte("fused")
            )

        max_trending = func.max(Event.trending_score).over()
        age_hours = (
            cast(
                func.extract(
                    "epoch", literal(now) - Event.last_updated_at
                ),
                Float,
            )
            / 3600.0
        )
        trending_norm = func.least(
            1.0,
            Event.trending_score
            / func.greatest(max_trending, literal(1.0)),
        )
        boost = (
            1.0
            + RECENCY_WEIGHT * func.exp(-age_hours / RECENCY_WINDOW_HOURS)
            + TRENDING_WEIGHT * trending_norm
        )
        score = fused.c.rrf * boost

        return (
            select(
                Event.id,
                Event.ai_headline,
                Event.ai_summary,
                Event.category,
                Event.category_color,
                Event.impact_level,
                Event.status,
                Event.trending_score,
                Event.last_updated_at,
                Event.first_reported_at,
                Event.location_name,
                ST_Y(Event.location).label("latitude"),
                ST_X(Event.location).label("longitude"),
                fused.c.lexical_rank,
                fused.c.semantic_rank,
                fused.c.semantic_similarity,
                fused.c.rrf,
                age_hours.label("age_hours"),
                trending_norm.label("trending_norm"),
                boost.label("boost"),
                score.label("score"),
            )
            .select_from(fused.join(Event, fused.c.id == Event.id))
            .order_by(score.desc())
            .limit(self._top_k)
        )

    def _eligibility_conditions(
        self,
        *,
        scope: SearchScope,
        bbox: BoundingBox | None,
        filters: SearchFilters | None,
        now: datetime,
        cutoff: datetime,
    ) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = [
            Event.status.in_([EventStatus.ACTIVE, EventStatus.STALE]),
            Event.last_updated_at >= cutoff,
        ]

        if scope is SearchScope.VIEWPORT and bbox is not None:
            conditions.append(Event.location.is_not(None))
            conditions.append(self._bbox_predicate(bbox))

        if filters is not None:
            if filters.category:
                conditions.append(
                    func.upper(Event.category) == filters.category.upper()
                )
            if filters.start:
                conditions.append(
                    Event.last_updated_at >= max(_naive_utc(filters.start), cutoff)
                )
            if filters.end:
                conditions.append(
                    Event.first_reported_at <= min(_naive_utc(filters.end), now)
                )

        return conditions

    def _bbox_predicate(self, bbox: BoundingBox) -> ColumnElement[bool]:
        if bbox.west > bbox.east:
            return or_(
                ST_Within(
                    Event.location,
                    ST_MakeEnvelope(bbox.west, bbox.south, 180.0, bbox.north, 4326),
                ),
                ST_Within(
                    Event.location,
                    ST_MakeEnvelope(-180.0, bbox.south, bbox.east, bbox.north, 4326),
                ),
            )
        return ST_Within(
            Event.location,
            ST_MakeEnvelope(bbox.west, bbox.south, bbox.east, bbox.north, 4326),
        )

    async def _load_context(self, events: list[SearchEvent]) -> None:
        if not events:
            return
        event_ids = [event.id for event in events]
        articles = await self._load_articles(event_ids)
        timelines = await self._load_timelines(event_ids)
        for event in events:
            event.articles = articles.get(event.id, [])
            event.timeline = timelines.get(event.id)

    async def _load_articles(
        self, event_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, list[SearchArticle]]:
        rank = (
            func.row_number()
            .over(
                partition_by=Article.event_id,
                order_by=(
                    Article.published_at.desc().nullslast(),
                    Article.ingested_at.desc(),
                    Article.id,
                ),
            )
            .label("rank")
        )
        ranked = (
            select(
                Article.id.label("id"),
                Article.event_id.label("event_id"),
                Article.title.label("title"),
                Article.url.label("url"),
                Article.published_at.label("published_at"),
                Source.name.label("source_name"),
                rank,
            )
            .join(Source, Source.id == Article.source_id)
            .where(Article.event_id.in_(event_ids))
            .subquery("ranked_articles")
        )
        stmt = (
            select(
                ranked.c.id,
                ranked.c.event_id,
                ranked.c.title,
                ranked.c.url,
                ranked.c.published_at,
                ranked.c.source_name,
            )
            .where(ranked.c.rank <= self._articles_per_event)
            .order_by(ranked.c.event_id, ranked.c.rank)
        )
        result = await self._session.execute(stmt)
        grouped: dict[uuid.UUID, list[SearchArticle]] = {}
        for article_id, event_id, title, url, published_at, source_name in result.all():
            article = SearchArticle(
                id=article_id,
                event_id=event_id,
                title=title,
                url=url,
                published_at=published_at,
                source_name=source_name,
            )
            grouped.setdefault(event_id, []).append(article)
        return grouped

    async def _load_timelines(
        self, event_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, SearchTimeline]:
        stmt = select(
            EventTl.event_id,
            EventTl.nodes,
            EventTl.edges,
            EventTl.tl_summary,
        ).where(
            EventTl.event_id.in_(event_ids),
            EventTl.status == EventTlStatus.READY,
        )
        result = await self._session.execute(stmt)
        timelines: dict[uuid.UUID, SearchTimeline] = {}
        for event_id, nodes, edges, summary in result.all():
            parsed = self._parse_timeline(
                event_id=event_id, nodes=nodes, edges=edges, summary=summary
            )
            if parsed is not None:
                timelines[event_id] = parsed
        return timelines

    def _parse_timeline(
        self,
        *,
        event_id: uuid.UUID,
        nodes: object,
        edges: object,
        summary: object,
    ) -> SearchTimeline | None:
        parsed_nodes: list[SearchTimelineNode] = []
        if isinstance(nodes, list):
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                try:
                    parsed_nodes.append(SearchTimelineNode.model_validate(node))
                except ValidationError as exc:
                    logger.warning(
                        "skipping malformed timeline node for event %s: %s.",
                        event_id,
                        exc,
                    )

        parsed_edges: list[SearchTimelineEdge] = []
        if isinstance(edges, list):
            for edge in edges:
                if not isinstance(edge, dict):
                    continue
                try:
                    parsed_edges.append(SearchTimelineEdge.model_validate(edge))
                except ValidationError as exc:
                    logger.warning(
                        "skipping malformed timeline edge for event %s: %s.",
                        event_id,
                        exc,
                    )

        summary_text = summary if isinstance(summary, str) else ""
        if not parsed_nodes and not parsed_edges and not summary_text.strip():
            return None
        return SearchTimeline(
            summary=summary_text,
            nodes=parsed_nodes,
            edges=parsed_edges,
        )

    def _event_from_row(self, row: Mapping[str, object]) -> SearchEvent:
        return SearchEvent(
            id=uuid.UUID(str(row["id"])),
            ai_headline=str(row["ai_headline"]),
            ai_summary=(
                None if row["ai_summary"] is None else str(row["ai_summary"])
            ),
            category=str(row["category"]),
            category_color=str(row["category_color"]),
            impact_level=ImpactLevel(str(row["impact_level"])),
            status=EventStatus(str(row["status"])),
            trending_score=_as_float(row["trending_score"]),
            last_updated_at=_as_datetime(row["last_updated_at"]),
            first_reported_at=_as_datetime(row["first_reported_at"]),
            location_name=(
                None if row["location_name"] is None else str(row["location_name"])
            ),
            latitude=_as_optional_float(row["latitude"]),
            longitude=_as_optional_float(row["longitude"]),
            lexical_rank=_as_optional_int(row["lexical_rank"]),
            semantic_rank=_as_optional_int(row["semantic_rank"]),
            semantic_similarity=_as_optional_float(row["semantic_similarity"]),
            rrf=_as_float(row["rrf"]),
            age_hours=_as_float(row["age_hours"]),
            trending_norm=_as_float(row["trending_norm"]),
            boost=_as_float(row["boost"]),
            score=_as_float(row["score"]),
        )
