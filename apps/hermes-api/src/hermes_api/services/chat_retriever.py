from __future__ import annotations
import logging
from collections.abc import Callable
from typing import Protocol
from hermes_ai.chat.models import (
    ChatScope,
    Coverage,
    CoverageLevel,
    DegradedFlag,
    RetrievalFilters,
    RetrievalResult,
    RetrievedArticle,
    RetrievedEvidence,
    RetrievedTimeline,
    RetrievedTimelineEdge,
    RetrievedTimelineNode,
)
from hermes_db.services.search import (
    BoundingBox,
    SearchArticle,
    SearchEvent,
    SearchFilters,
    SearchScope,
    SearchService,
    SearchTimeline,
)
from hermes_db.session import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


def _article(article: SearchArticle) -> RetrievedArticle:
    return RetrievedArticle(
        id=article.id,
        event_id=article.event_id,
        title=article.title,
        url=article.url,
        source_name=article.source_name,
        published_at=article.published_at,
    )

def _timeline(timeline: SearchTimeline | None) -> RetrievedTimeline | None:
    if timeline is None:
        return None
    return RetrievedTimeline(
        summary=timeline.summary,
        nodes=[
            RetrievedTimelineNode(
                id=node.id,
                date=node.date,
                headline=node.headline,
                summary=node.summary,
                location_name=node.location_name,
                latitude=node.latitude,
                longitude=node.longitude,
                category_color=node.category_color,
            )
            for node in timeline.nodes
        ],
        edges=[
            RetrievedTimelineEdge(
                source_node_id=edge.source_node_id,
                target_node_id=edge.target_node_id,
                relationship=edge.relationship,
            )
            for edge in timeline.edges
        ],
    )

def _evidence(event: SearchEvent) -> RetrievedEvidence:
    return RetrievedEvidence(
        event_id=event.id,
        headline=event.ai_headline,
        summary=event.ai_summary,
        category=event.category,
        category_color=event.category_color,
        impact_level=event.impact_level.value,
        status=event.status.value,
        location_name=event.location_name,
        latitude=event.latitude,
        longitude=event.longitude,
        first_reported_at=event.first_reported_at,
        last_updated_at=event.last_updated_at,
        age_hours=event.age_hours,
        trending_score=event.trending_score,
        lexical_rank=event.lexical_rank,
        semantic_similarity=event.semantic_similarity,
        rrf=event.rrf,
        articles=[_article(article) for article in event.articles],
        timeline=_timeline(event.timeline),
    )


class EmbeddingClient(Protocol):
    async def gen_embeddings(self, texts: list[str]) -> list[list[float] | None]: ...

class DbChatRetriever:
    def __init__(
        self,
        llm: EmbeddingClient,
        *,
        top_k: int,
        min_local_results: int,
        min_semantic_similarity: float,
        freshness_hours: float,
        session_factory: Callable[[], AsyncSession] | None = None,
    ) -> None:
        self._llm = llm
        self._top_k = top_k
        self._min_local_results = min_local_results
        self._min_semantic_similarity = min_semantic_similarity
        self._freshness_hours = freshness_hours
        self._session_factory: Callable[[], AsyncSession] = (
            session_factory or AsyncSessionLocal
        )

    async def _embed_query(self, query: str) -> list[float] | None:
        try:
            embeddings = await self._llm.gen_embeddings([query])
        except Exception as exc:
            logger.warning(
                "chat query embedding failed; using lexical retrieval: %s.",
                exc,
            )
            return None
        if not embeddings:
            return None
        return embeddings[0]


    async def retrieve(
        self,
        query: str,
        *,
        scope: ChatScope,
        filters: RetrievalFilters | None = None,
        recency_intent: bool = False,
    ) -> RetrievalResult:
        embedding = await self._embed_query(query)

        async with self._session_factory() as session:
            service = SearchService(
                session,
                top_k=self._top_k,
                min_local_results=self._min_local_results,
                min_semantic_similarity=self._min_semantic_similarity,
                freshness_hours=self._freshness_hours,
            )
            result = await service.retrieve(
                query,
                scope=SearchScope(scope.type.value),
                event_id=scope.event_id,
                bbox=(
                    BoundingBox(
                        north=scope.bbox.north,
                        south=scope.bbox.south,
                        east=scope.bbox.east,
                        west=scope.bbox.west,
                    ) if scope.bbox is not None else None
                ),
                filters=(
                    SearchFilters(
                        category=filters.category,
                        start=filters.start,
                        end=filters.end,
                    ) if filters is not None else None
                ),
                embedding=embedding,
                recency_intent=recency_intent,
            )

        logger.debug(
            "chat retrieval returned %d events with %s coverage.",
            len(result.events),
            result.coverage.level.value,
        )
        return RetrievalResult(
            evidence=[_evidence(event) for event in result.events],
            coverage=Coverage(
                level=CoverageLevel(result.coverage.level.value),
                result_count=result.coverage.result_count,
                best_semantic_similarity=result.coverage.best_semantic_similarity,
                best_lexical_rank=result.coverage.best_lexical_rank,
                newest_age_hours=result.coverage.newest_age_hours,
                recency_stale=result.coverage.recency_stale,
            ),
            degraded=[DegradedFlag(flag.value) for flag in result.degraded],
        )


__all__ = ["DbChatRetriever", "EmbeddingClient"]
