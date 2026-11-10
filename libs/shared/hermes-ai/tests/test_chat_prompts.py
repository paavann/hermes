"""Snapshot and escaping tests for the answer prompt."""

import uuid
from datetime import UTC, datetime

from hermes_ai.chat.citations import CitationRegistry
from hermes_ai.chat.models import (
    ChatScope,
    Coverage,
    CoverageLevel,
    RetrievedArticle,
    RetrievedEvidence,
    RetrievedTimeline,
    RetrievedTimelineEdge,
    RetrievedTimelineNode,
    ScopeType,
    WebResult,
)
from hermes_ai.chat.prompts import (
    ANSWER_SYSTEM_PROMPT,
    build_answer_messages,
    clean_xml_text,
    format_evidence,
)


NOW = datetime(2026, 11, 7, tzinfo=UTC)


def _event(
    *,
    headline: str = "Flooding in Valencia",
    summary: str = "Severe flooding.",
    article_count: int = 1,
    node_count: int = 1,
) -> RetrievedEvidence:
    event_id = uuid.uuid4()
    return RetrievedEvidence(
        event_id=event_id,
        headline=headline,
        summary=summary,
        category="DISASTER",
        impact_level="HIGH",
        status="ACTIVE",
        location_name="Valencia",
        latitude=39.47,
        longitude=-0.37,
        first_reported_at=NOW,
        last_updated_at=NOW,
        articles=[
            RetrievedArticle(
                id=uuid.uuid4(),
                event_id=event_id,
                title=f"Article {index}",
                url=f"https://example.com/{index}",
                source_name="Example News",
                published_at=NOW,
            )
            for index in range(article_count)
        ],
        timeline=(
            RetrievedTimeline(
                summary="Escalation timeline.",
                nodes=[
                    RetrievedTimelineNode(
                        id=f"node-{index}",
                        date=f"2026-11-0{index + 1}",
                        headline=f"Node {index}",
                        summary=f"Step {index}.",
                    )
                    for index in range(node_count)
                ],
                edges=[
                    RetrievedTimelineEdge(
                        source_node_id="node-0",
                        target_node_id="node-1",
                        relationship="caused",
                    )
                ]
                if node_count > 1
                else [],
            )
            if node_count
            else None
        ),
    )


def _web(index: int = 0) -> WebResult:
    return WebResult(
        title=f"Web report {index}",
        url=f"https://news.example.com/{index}",
        source_name="news.example.com",
        retrieved_at=NOW,
        snippet=f"Snippet {index}.",
    )


def test_minimal_evidence_snapshot() -> None:
    registry = CitationRegistry.build([_event(article_count=0, node_count=0)])

    rendered = format_evidence(registry, web_available=False)

    assert rendered == (
        "<local_evidence>\n"
        "  <E1>\n"
        "    <headline>Flooding in Valencia</headline>\n"
        "    <summary>Severe flooding.</summary>\n"
        "    <category>DISASTER</category>\n"
        "    <impact_level>HIGH</impact_level>\n"
        "    <status>ACTIVE</status>\n"
        "    <location>Valencia</location>\n"
        "    <first_reported_at>2026-11-07T00:00:00+00:00</first_reported_at>\n"
        "    <last_updated_at>2026-11-07T00:00:00+00:00</last_updated_at>\n"
        "  </E1>\n"
        "</local_evidence>\n"
        '<web_evidence available="false">'
        "External search was unavailable for this turn."
        "</web_evidence>"
    )


def test_article_and_timeline_blocks_use_stable_markers() -> None:
    registry = CitationRegistry.build([_event(node_count=2)], [_web()])

    rendered = format_evidence(registry, web_available=True)

    assert "<articles>" in rendered
    assert "<A1>" in rendered
    assert "<title>Article 0</title>" in rendered
    assert "<timeline>" in rendered
    assert '<node marker="T1">' in rendered
    assert '<edge from="T1" to="T2">caused</edge>' in rendered
    assert '<web_evidence available="true">' in rendered
    assert "<W1>" in rendered
    assert "<snippet>Snippet 0.</snippet>" in rendered


def test_evidence_escapes_injection_markup() -> None:
    headline = '<script>alert("x")</script> & "quoted"'
    registry = CitationRegistry.build(
        [_event(headline=headline, article_count=0, node_count=0)]
    )

    rendered = format_evidence(registry, web_available=False)

    assert "<script>" not in rendered
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in rendered
    assert "&amp;" in rendered


def test_clean_xml_text_caps_after_normalizing() -> None:
    assert clean_xml_text("  a\n\nb\tc  ", limit=3) == "a b"
    assert len(clean_xml_text("x" * 100, limit=10)) == 10


def test_evidence_applies_per_field_caps() -> None:
    event = _event(
        summary="s" * 2000,
        article_count=6,
        node_count=15,
    )
    event.articles[0].title = "t" * 500
    event.timeline.summary = "u" * 2000  # type: ignore[union-attr]
    registry = CitationRegistry.build([event], [_web(index) for index in range(5)])

    rendered = format_evidence(registry, web_available=True)

    assert "s" * 1200 in rendered
    assert "s" * 1201 not in rendered
    assert "t" * 300 in rendered
    assert "t" * 301 not in rendered
    assert "u" * 1500 in rendered
    assert "u" * 1501 not in rendered
    assert "<A5>" in rendered
    assert "<A6>" not in rendered
    assert '<node marker="T12">' in rendered
    assert '<node marker="T13">' not in rendered
    assert "<W3>" in rendered
    assert "<W4>" not in rendered


def test_answer_messages_include_rules_scope_and_question() -> None:
    registry = CitationRegistry.build([_event()], [_web()])
    scope = ChatScope(type=ScopeType.GLOBAL)
    coverage = Coverage(level=CoverageLevel.THIN, result_count=1)

    messages = build_answer_messages(
        registry=registry,
        message="What happened? <b>",
        scope=scope,
        web_available=True,
        coverage=coverage,
        now=NOW,
    )

    system = str(messages[0].content)
    human = str(messages[1].content)
    assert system.startswith(ANSWER_SYSTEM_PROMPT.splitlines()[0])
    assert "[BG]" in system
    assert "Article bodies are not stored" in system
    assert "conflict" in system
    assert "untrusted" in system
    assert "Never invent IDs" in system
    assert "Today is 2026-11-07." in system
    assert "<scope>all eligible plottings.</scope>" in human
    assert "<coverage>thin (1 local results)</coverage>" in human
    assert "<user_question>What happened? &lt;b&gt;</user_question>" in human
    assert "<W1>" in human


def test_answer_messages_note_unavailable_web() -> None:
    registry = CitationRegistry.build([_event()])

    messages = build_answer_messages(
        registry=registry,
        message="question",
        scope=ChatScope(type=ScopeType.GLOBAL),
        web_available=False,
        now=NOW,
    )

    human = str(messages[1].content)
    assert '<web_evidence available="false">' in human
    assert "External search was unavailable" in human
