"""Immutable citation evidence and validation data structures."""

from __future__ import annotations

from dataclasses import dataclass

from hermes_ai.chat.models import (
    RetrievedArticle,
    RetrievedEvidence,
    RetrievedTimelineNode,
    WebResult,
)


@dataclass(frozen=True, slots=True)
class ArticleEvidence:
    marker: str
    article: RetrievedArticle


@dataclass(frozen=True, slots=True)
class TimelineNodeEvidence:
    """Indexed timeline node backing a ``[T#]`` citation marker."""

    marker: str
    node: RetrievedTimelineNode


@dataclass(frozen=True, slots=True)
class TimelineEdgeEvidence:
    """Causal edge linking two indexed timeline node markers."""

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
    """Indexed external web search result backing a ``[W#]`` marker."""

    marker: str
    result: WebResult


@dataclass(frozen=True, slots=True)
class CitationValidation:
    """Summary of sanitized citations extracted from a completed answer."""

    cleaned_text: str
    cited_markers: tuple[str, ...]
    removed_count: int
    has_background: bool
    has_citation: bool


__all__ = [
    "ArticleEvidence",
    "CitationValidation",
    "EventEvidence",
    "TimelineEdgeEvidence",
    "TimelineNodeEvidence",
    "WebEvidence",
]
