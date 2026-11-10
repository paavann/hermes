"""Tests for evidence registry and streaming citation validation."""

import uuid
from datetime import UTC, datetime

from hermes_ai.chat.citations import (
    CitationRegistry,
    CitationStreamFilter,
    finalize_answer,
)
from hermes_ai.chat.models import (
    ChatSourceKind,
    RetrievedArticle,
    RetrievedEvidence,
    RetrievedTimeline,
    RetrievedTimelineEdge,
    RetrievedTimelineNode,
    WebResult,
)


def _event(
    *,
    headline: str = "Flooding in Valencia",
    article_count: int = 1,
    timeline: bool = True,
) -> RetrievedEvidence:
    event_id = uuid.uuid4()
    now = datetime(2026, 11, 7, tzinfo=UTC)
    articles = [
        RetrievedArticle(
            id=uuid.uuid4(),
            event_id=event_id,
            title=f"Article {index}",
            url=f"https://example.com/{index}",
            source_name="Example News",
            published_at=now,
        )
        for index in range(article_count)
    ]
    return RetrievedEvidence(
        event_id=event_id,
        headline=headline,
        summary="Severe flooding.",
        category="DISASTER",
        impact_level="HIGH",
        status="ACTIVE",
        location_name="Valencia",
        latitude=39.47,
        longitude=-0.37,
        first_reported_at=now,
        last_updated_at=now,
        articles=articles,
        timeline=(
            RetrievedTimeline(
                summary="Escalation timeline.",
                nodes=[
                    RetrievedTimelineNode(
                        id="node-a",
                        date="2026-11-01",
                        headline="Rain begins",
                        summary="Storm arrives.",
                        location_name="Valencia",
                    ),
                    RetrievedTimelineNode(
                        id="node-b",
                        date="2026-11-02",
                        headline="Flooding",
                        summary="Rivers overflow.",
                    ),
                ],
                edges=[
                    RetrievedTimelineEdge(
                        source_node_id="node-a",
                        target_node_id="node-b",
                        relationship="caused",
                    )
                ],
            )
            if timeline
            else None
        ),
    )


def _registry(events: int = 1) -> CitationRegistry:
    web = [
        WebResult(
            title="Web report",
            url="https://news.example.com/report",
            source_name="news.example.com",
            published_at=None,
            retrieved_at=datetime(2026, 11, 7, tzinfo=UTC),
            snippet="External details.",
        )
    ]
    return CitationRegistry.build(
        [_event(headline=f"Event {index}") for index in range(events)],
        web,
    )


def test_registry_assigns_stable_markers_in_order() -> None:
    registry = _registry(events=2)

    assert [event.marker for event in registry.events] == ["E1", "E2"]
    assert [article.marker for article in registry.events[0].articles] == ["A1"]
    assert [article.marker for article in registry.events[1].articles] == ["A2"]
    assert [node.marker for node in registry.events[0].timeline_nodes] == [
        "T1",
        "T2",
    ]
    assert [node.marker for node in registry.events[1].timeline_nodes] == [
        "T3",
        "T4",
    ]
    assert [web.marker for web in registry.web] == ["W1"]
    assert registry.events[0].timeline_edges[0].source_marker == "T1"


def test_registry_resolves_sources_with_parent_coordinates() -> None:
    registry = _registry()
    parent = registry.events[0].event

    event_source = registry.resolve("E1")
    article_source = registry.resolve("[A1]")
    timeline_source = registry.resolve("T1")
    web_source = registry.resolve("W1")

    assert event_source is not None
    assert event_source.kind is ChatSourceKind.EVENT
    assert event_source.event_id == parent.event_id
    assert event_source.latitude == parent.latitude

    assert article_source is not None
    assert article_source.kind is ChatSourceKind.ARTICLE
    assert article_source.event_id == parent.event_id
    assert article_source.url == "https://example.com/0"

    assert timeline_source is not None
    assert timeline_source.kind is ChatSourceKind.TIMELINE
    assert timeline_source.event_id == parent.event_id
    assert timeline_source.published_at is not None

    assert web_source is not None
    assert web_source.kind is ChatSourceKind.WEB
    assert web_source.is_external is True


def test_sources_for_deduplicates_in_first_citation_order() -> None:
    registry = _registry()
    sources = registry.sources_for(["A1", "E1", "A1", "BG", "T1"])

    assert [source.kind for source in sources] == [
        ChatSourceKind.ARTICLE,
        ChatSourceKind.EVENT,
        ChatSourceKind.TIMELINE,
    ]


def test_stream_filter_handles_split_markers_across_chunks() -> None:
    registry = _registry()
    stream = CitationStreamFilter(registry)

    first = stream.feed("Answer [E")
    second = stream.feed("1] and [A")
    third = stream.feed("1]. [E99] [BG]")
    final = stream.flush()

    assert first == "Answer "
    assert second == "[E1] and "
    assert third == "[A1].  [BG]"
    assert final == ""
    assert stream.cited_markers == ("E1", "A1")
    assert stream.removed_count == 1


def test_stream_filter_splits_comma_separated_markers() -> None:
    registry = _registry(events=2)
    stream = CitationStreamFilter(registry)

    output = stream.feed("Both [E1, E2] and [BG].")

    assert output == "Both [E1][E2] and [BG]."
    assert stream.cited_markers == ("E1", "E2")


def test_stream_filter_drops_unknown_markers_but_keeps_known_ones() -> None:
    registry = _registry()
    stream = CitationStreamFilter(registry)

    output = stream.feed("[E1, E99]")

    assert output == "[E1]"
    assert stream.removed_count == 1


def test_stream_filter_preserves_non_citation_brackets() -> None:
    registry = _registry()
    stream = CitationStreamFilter(registry)

    assert stream.feed("[citation needed]") == "[citation needed]"


def test_stream_filter_records_repeated_marker_once() -> None:
    registry = _registry()
    stream = CitationStreamFilter(registry)

    output = stream.feed("[E1] then [E1]")

    assert output == "[E1] then [E1]"
    assert stream.cited_markers == ("E1",)


def test_stream_filter_flushes_incomplete_marker() -> None:
    registry = _registry()
    stream = CitationStreamFilter(registry)

    assert stream.feed("Partial [E1") == "Partial "
    assert stream.flush() == ""


def test_finalize_answer_reports_no_citations() -> None:
    registry = _registry()

    validation = finalize_answer("This is a general answer.", registry)

    assert validation.cleaned_text == "This is a general answer."
    assert validation.cited_markers == ()
    assert validation.has_citation is False
    assert validation.has_background is False


def test_finalize_answer_filters_unknown_ids_and_tracks_background() -> None:
    registry = _registry()

    validation = finalize_answer("[BG] General context. [E1] Local. [E99]", registry)

    assert validation.cleaned_text == "[BG] General context. [E1] Local. "
    assert validation.cited_markers == ("E1",)
    assert validation.has_background is True
    assert validation.has_citation is True
    assert validation.removed_count == 1
