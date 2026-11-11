"""Evidence ID assignment and source resolution registry."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from hermes_ai.chat.citations.types import (
    ArticleEvidence,
    EventEvidence,
    TimelineEdgeEvidence,
    TimelineNodeEvidence,
    WebEvidence,
)
from hermes_ai.chat.models import (
    ChatSource,
    ChatSourceKind,
    RetrievedEvidence,
    WebResult,
)


@dataclass(frozen=True, slots=True)
class CitationRegistry:
    events: tuple[EventEvidence, ...]
    web: tuple[WebEvidence, ...] = ()
    _sources: dict[str, ChatSource] = field(init=False, repr=False)
    _web_by_marker: dict[str, WebEvidence] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        sources: dict[str, ChatSource] = {}
        web_by_marker: dict[str, WebEvidence] = {}
        for event in self.events:
            sources[event.marker] = _event_source(event)
            for article in event.articles:
                sources[article.marker] = _article_source(event, article)
            for node in event.timeline_nodes:
                sources[node.marker] = _timeline_source(event, node)
        for web in self.web:
            sources[web.marker] = _web_source(web)
            web_by_marker[web.marker] = web
        object.__setattr__(self, "_sources", sources)
        object.__setattr__(self, "_web_by_marker", web_by_marker)

    @classmethod
    def build(
        cls,
        events: Sequence[RetrievedEvidence],
        web_results: Sequence[WebResult] = (),
    ) -> CitationRegistry:
        """Build a registry with sequential ``E#``, ``A#``, ``T#``, and ``W#`` IDs."""
        event_records: list[EventEvidence] = []
        article_index = 1
        node_index = 1
        for event_index, event in enumerate(events, start=1):
            record, article_index, node_index = _build_event_evidence(
                event_index,
                event,
                article_index,
                node_index,
            )
            event_records.append(record)
        web_records = tuple(
            WebEvidence(marker=f"W{index}", result=result)
            for index, result in enumerate(web_results, start=1)
        )
        return cls(events=tuple(event_records), web=web_records)

    def resolve(self, marker: str) -> ChatSource | None:
        return self._sources.get(_normalize_marker(marker))

    def sources_for(self, markers: Sequence[str]) -> list[ChatSource]:
        """Return deduplicated ``ChatSource`` records in first-citation order."""
        sources: list[ChatSource] = []
        seen: set[str] = set()
        for marker in markers:
            normalized = _normalize_marker(marker)
            if normalized in seen or normalized == "BG":
                continue
            source = self._sources.get(normalized)
            if source is None:
                continue
            seen.add(normalized)
            sources.append(source)
        return sources

    def web_evidence(self, marker: str) -> WebEvidence | None:
        """Return the indexed ``WebEvidence`` record for a ``W#`` marker."""
        return self._web_by_marker.get(_normalize_marker(marker))

    @property
    def markers(self) -> frozenset[str]:
        """All registered evidence marker strings."""
        return frozenset(self._sources)


def _build_event_evidence(
    event_index: int,
    event: RetrievedEvidence,
    article_index: int,
    node_index: int,
) -> tuple[EventEvidence, int, int]:
    articles: list[ArticleEvidence] = []
    for article in event.articles:
        articles.append(ArticleEvidence(marker=f"A{article_index}", article=article))
        article_index += 1

    nodes, edges, node_index = _build_timeline_evidence(event, node_index)
    record = EventEvidence(
        marker=f"E{event_index}",
        event=event,
        articles=tuple(articles),
        timeline_nodes=nodes,
        timeline_edges=edges,
        timeline_summary=(event.timeline.summary if event.timeline is not None else ""),
    )
    return record, article_index, node_index


def _build_timeline_evidence(
    event: RetrievedEvidence,
    node_index: int,
) -> tuple[tuple[TimelineNodeEvidence, ...], tuple[TimelineEdgeEvidence, ...], int]:
    if event.timeline is None:
        return (), (), node_index

    node_markers: dict[str, str] = {}
    nodes: list[TimelineNodeEvidence] = []
    for node in event.timeline.nodes:
        marker = f"T{node_index}"
        node_markers[node.id] = marker
        nodes.append(TimelineNodeEvidence(marker=marker, node=node))
        node_index += 1

    edges: list[TimelineEdgeEvidence] = []
    for edge in event.timeline.edges:
        source_marker = node_markers.get(edge.source_node_id)
        target_marker = node_markers.get(edge.target_node_id)
        if source_marker and target_marker:
            edges.append(
                TimelineEdgeEvidence(
                    source_marker=source_marker,
                    target_marker=target_marker,
                    relationship=edge.relationship,
                )
            )
    return tuple(nodes), tuple(edges), node_index


def _normalize_marker(marker: str) -> str:
    return marker.strip().removeprefix("[").removesuffix("]").strip().upper()


def _event_source(event: EventEvidence) -> ChatSource:
    evidence = event.event
    return ChatSource(
        kind=ChatSourceKind.EVENT,
        id=str(evidence.event_id),
        event_id=evidence.event_id,
        title=evidence.headline,
        latitude=evidence.latitude,
        longitude=evidence.longitude,
    )


def _article_source(event: EventEvidence, article: ArticleEvidence) -> ChatSource:
    evidence = event.event
    return ChatSource(
        kind=ChatSourceKind.ARTICLE,
        id=str(article.article.id),
        event_id=evidence.event_id,
        title=article.article.title,
        url=article.article.url,
        source_name=article.article.source_name,
        published_at=article.article.published_at,
        latitude=evidence.latitude,
        longitude=evidence.longitude,
    )


def _timeline_source(event: EventEvidence, node: TimelineNodeEvidence) -> ChatSource:
    evidence = event.event
    return ChatSource(
        kind=ChatSourceKind.TIMELINE,
        id=f"{evidence.event_id}:{node.node.id}",
        event_id=evidence.event_id,
        title=node.node.headline,
        published_at=_parse_date(node.node.date),
        latitude=(
            node.node.latitude if node.node.latitude is not None else evidence.latitude
        ),
        longitude=(
            node.node.longitude
            if node.node.longitude is not None
            else evidence.longitude
        ),
        snippet=node.node.summary,
    )


def _web_source(web: WebEvidence) -> ChatSource:
    result = web.result
    return ChatSource(
        kind=ChatSourceKind.WEB,
        id=result.url,
        title=result.title,
        url=result.url,
        source_name=result.source_name,
        published_at=result.published_at,
        retrieved_at=result.retrieved_at,
        is_external=True,
        snippet=result.snippet,
    )


def _parse_date(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


__all__ = ["CitationRegistry"]
