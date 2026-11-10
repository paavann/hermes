"""Evidence registry and streaming citation validation."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from hermes_ai.chat.models import (
    ChatSource,
    ChatSourceKind,
    RetrievedArticle,
    RetrievedEvidence,
    RetrievedTimelineNode,
    WebResult,
)


MARKER_RE = re.compile(
    r"\[(BG|[EATW]\d+)(?:\s*,\s*(?:BG|[EATW]\d+))*\]",
    re.IGNORECASE,
)
MARKER_TOKEN_RE = re.compile(r"^(?:BG|[EATW]\d+)$", re.IGNORECASE)
MAX_MARKER_HOLD_CHARS = 17


@dataclass(frozen=True, slots=True)
class ArticleEvidence:
    marker: str
    article: RetrievedArticle


@dataclass(frozen=True, slots=True)
class TimelineNodeEvidence:
    marker: str
    node: RetrievedTimelineNode


@dataclass(frozen=True, slots=True)
class TimelineEdgeEvidence:
    source_marker: str
    target_marker: str
    relationship: str


@dataclass(frozen=True, slots=True)
class EventEvidence:
    marker: str
    event: RetrievedEvidence
    articles: tuple[ArticleEvidence, ...] = ()
    timeline_nodes: tuple[TimelineNodeEvidence, ...] = ()
    timeline_edges: tuple[TimelineEdgeEvidence, ...] = ()
    timeline_summary: str = ""


@dataclass(frozen=True, slots=True)
class WebEvidence:
    marker: str
    result: WebResult


@dataclass(frozen=True, slots=True)
class CitationValidation:
    cleaned_text: str
    cited_markers: tuple[str, ...]
    removed_count: int
    has_background: bool
    has_citation: bool


@dataclass(slots=True)
class CitationRegistry:
    """Assigns stable evidence IDs and resolves them back to chat sources."""

    events: tuple[EventEvidence, ...]
    web: tuple[WebEvidence, ...] = ()
    _sources: dict[str, ChatSource] = field(init=False, repr=False)
    _web_by_marker: dict[str, WebEvidence] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._sources = {}
        self._web_by_marker = {}
        for event in self.events:
            self._sources[event.marker] = _event_source(event)
            for article in event.articles:
                self._sources[article.marker] = _article_source(event, article)
            for node in event.timeline_nodes:
                self._sources[node.marker] = _timeline_source(event, node)
        for web in self.web:
            self._sources[web.marker] = _web_source(web)
            self._web_by_marker[web.marker] = web

    @classmethod
    def build(
        cls,
        events: Sequence[RetrievedEvidence],
        web_results: Sequence[WebResult] = (),
    ) -> CitationRegistry:
        event_records: list[EventEvidence] = []
        article_index = 1
        node_index = 1
        for event_index, event in enumerate(events, start=1):
            articles: list[ArticleEvidence] = []
            for article in event.articles:
                articles.append(
                    ArticleEvidence(marker=f"A{article_index}", article=article)
                )
                article_index += 1

            node_markers: dict[str, str] = {}
            nodes: list[TimelineNodeEvidence] = []
            if event.timeline is not None:
                for node in event.timeline.nodes:
                    marker = f"T{node_index}"
                    node_markers[node.id] = marker
                    nodes.append(TimelineNodeEvidence(marker=marker, node=node))
                    node_index += 1

            edges: list[TimelineEdgeEvidence] = []
            if event.timeline is not None:
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

            event_records.append(
                EventEvidence(
                    marker=f"E{event_index}",
                    event=event,
                    articles=tuple(articles),
                    timeline_nodes=tuple(nodes),
                    timeline_edges=tuple(edges),
                    timeline_summary=(
                        event.timeline.summary if event.timeline is not None else ""
                    ),
                )
            )

        web_records = tuple(
            WebEvidence(marker=f"W{index}", result=result)
            for index, result in enumerate(web_results, start=1)
        )
        return cls(events=tuple(event_records), web=web_records)

    def resolve(self, marker: str) -> ChatSource | None:
        return self._sources.get(_normalize_marker(marker))

    def sources_for(self, markers: Sequence[str]) -> list[ChatSource]:
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
        return self._web_by_marker.get(_normalize_marker(marker))

    @property
    def markers(self) -> frozenset[str]:
        return frozenset(self._sources)


class CitationStreamFilter:
    """Removes invalid markers while holding split markers across chunks."""

    def __init__(self, registry: CitationRegistry) -> None:
        self._registry = registry
        self._buffer = ""
        self._cited: list[str] = []
        self._seen: set[str] = set()
        self._removed = 0

    @property
    def cited_markers(self) -> tuple[str, ...]:
        return tuple(self._cited)

    @property
    def removed_count(self) -> int:
        return self._removed

    def feed(self, text: str) -> str:
        self._buffer += text
        output: list[str] = []
        while self._buffer:
            start = self._buffer.find("[")
            if start == -1:
                output.append(self._buffer)
                self._buffer = ""
                break
            output.append(self._buffer[:start])
            remainder = self._buffer[start:]
            end = remainder.find("]")
            if end == -1:
                if len(remainder) <= MAX_MARKER_HOLD_CHARS:
                    self._buffer = remainder
                    break
                output.append("[")
                self._buffer = remainder[1:]
                continue
            candidate = remainder[: end + 1]
            output.append(self._render_candidate(candidate))
            self._buffer = remainder[end + 1 :]
        return "".join(output)

    def flush(self) -> str:
        remainder, self._buffer = self._buffer, ""
        if not remainder:
            return ""
        if "[" in remainder and "]" not in remainder:
            remainder = remainder.split("[", 1)[0]
        return remainder

    def _render_candidate(self, candidate: str) -> str:
        content = candidate[1:-1]
        tokens = [token.strip() for token in content.split(",")]
        if not tokens or not any(MARKER_TOKEN_RE.fullmatch(token) for token in tokens):
            return candidate

        rendered: list[str] = []
        for token in tokens:
            normalized = token.upper()
            if normalized == "BG":
                rendered.append("[BG]")
                continue
            if self._registry.resolve(normalized) is None:
                self._removed += 1
                continue
            if normalized not in self._seen:
                self._seen.add(normalized)
                self._cited.append(normalized)
            rendered.append(f"[{normalized}]")
        return "".join(rendered)


def finalize_answer(text: str, registry: CitationRegistry) -> CitationValidation:
    stream = CitationStreamFilter(registry)
    cleaned = stream.feed(text) + stream.flush()
    return CitationValidation(
        cleaned_text=cleaned,
        cited_markers=stream.cited_markers,
        removed_count=stream.removed_count,
        has_background="[BG]" in cleaned,
        has_citation=bool(stream.cited_markers),
    )


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


__all__ = [
    "ArticleEvidence",
    "CitationRegistry",
    "CitationStreamFilter",
    "CitationValidation",
    "EventEvidence",
    "TimelineEdgeEvidence",
    "TimelineNodeEvidence",
    "WebEvidence",
    "finalize_answer",
]
