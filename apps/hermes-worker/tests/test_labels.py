import uuid
from dataclasses import replace
from datetime import UTC, datetime
from hermes_ai.models.labels import ArticleLabelExtraction
from hermes_db.enums import (
    ArticleBodySource,
    ArticleCategory,
    ArticleCertainty,
    ArticleType,
    EventForm,
    EventScope,
    SourceFetchPolicy,
)
from hermes_db.services import AnalysisArticle
from hermes_worker.jobs.fetch import FetchReason, FetchResult
from hermes_worker.jobs.labels import (
    GateDecision,
    LabelPayload,
    build_embedding_text,
    build_label_input,
    build_text_hashes,
    evaluate_gate,
    label_input_hash,
    select_text,
    to_label_payload,
)


NOW = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)


def _article(
    *,
    feed_summary: str | None = "A summary of the event.",
    fetch_policy: SourceFetchPolicy = SourceFetchPolicy.FULL_TEXT,
    paywall: bool = False,
) -> AnalysisArticle:
    return AnalysisArticle(
        id=uuid.uuid4(),
        title="Earthquake strikes coastal city",
        url="https://news.example.com/story",
        feed_summary=feed_summary,
        published_at=NOW,
        language="en",
        attempt_count=0,
        family_id=None,
        source_name="Example News",
        source_slug="example-news",
        source_origin_group="example",
        fetch_policy=fetch_policy,
        paywall=paywall,
    )


def _payload(**overrides: object) -> LabelPayload:
    base = LabelPayload(
        is_event=True,
        article_type=ArticleType.BREAKING,
        event_time=NOW,
        severity=3,
        scope=EventScope.CITY,
        confidence=0.82,
        fact="An earthquake struck the coastal city on Tuesday.",
        scale_facts={"deaths": 12},
        entities=[{"name": "Coastal City", "kind": "LOCATION"}],
        locations=[{"name": "Coastal City", "country_code": "EX"}],
        category=ArticleCategory.DISASTER,
        event_form=EventForm.INCIDENT,
        specificity=4,
        consequence=4,
        certainty=ArticleCertainty.REPORTED,
        reject_reason=None,
        input_hash="0" * 64,
        evidence_quote="An earthquake struck the coastal city on Tuesday.",
    )
    return replace(base, **overrides)


def test_gate_accepts_specific_single_incident() -> None:
    decision = evaluate_gate(_payload())

    assert decision == GateDecision(rejected=False)


def test_gate_rejects_non_event_at_label_stage() -> None:
    decision = evaluate_gate(
        _payload(
            is_event=False,
            event_form=None,
            reject_reason="opinion column, no specific occurrence",
        )
    )

    assert decision.rejected is True
    assert decision.stage is not None
    assert decision.stage.value == "LABEL"
    assert decision.reason is not None
    assert decision.reason.startswith("not_event:")


def test_gate_rejects_event_without_fact() -> None:
    decision = evaluate_gate(_payload(fact=None))

    assert decision.rejected is True
    assert decision.reason == "missing_fact"


def test_gate_rejects_opinion_feature_listing_and_analysis() -> None:
    for article_type in (
        ArticleType.ANALYSIS,
        ArticleType.FEATURE,
        ArticleType.LISTICLE,
        ArticleType.OPINION,
    ):
        decision = evaluate_gate(_payload(article_type=article_type))
        assert decision.rejected is True
        assert decision.reason == f"article_type_{article_type.value.lower()}"


def test_gate_rejects_low_specificity() -> None:
    decision = evaluate_gate(_payload(specificity=2))

    assert decision.rejected is True
    assert decision.reason == "low_specificity_2"


def test_gate_rejects_vague_policy_action() -> None:
    decision = evaluate_gate(
        _payload(event_form=EventForm.POLICY_ACTION, specificity=3)
    )

    assert decision.rejected is True
    assert decision.reason == "policy_action_low_specificity_3"


def test_gate_accepts_specific_policy_action() -> None:
    decision = evaluate_gate(
        _payload(event_form=EventForm.POLICY_ACTION, specificity=4)
    )

    assert decision.rejected is False


def test_gate_rejects_brazil_style_planned_policy_without_place_or_date() -> None:
    decision = evaluate_gate(
        _payload(
            is_event=False,
            article_type=ArticleType.DEVELOPMENT,
            event_form=EventForm.POLICY_ACTION,
            specificity=2,
            reject_reason=(
                "vague planned policy action without a specific place or date"
            ),
        )
    )

    assert decision.rejected is True
    assert decision.stage is not None
    assert decision.stage.value == "LABEL"


def test_select_text_prefers_fetched_body_for_full_text_source() -> None:
    article = _article()
    fetched = FetchResult(
        url=article.url,
        reason=FetchReason.OK,
        text="Full article body " * 40,
        http_status=200,
    )

    selected = select_text(article, fetched)

    assert selected.body_source == ArticleBodySource.FULL_TEXT
    assert selected.http_status == 200
    assert selected.word_count > 0
    assert 0.7 <= selected.input_quality <= 1.0


def test_select_text_uses_summary_for_paywalled_source() -> None:
    article = _article(paywall=True)
    fetched = FetchResult(
        url=article.url,
        reason=FetchReason.OK,
        text="Full article body " * 40,
        http_status=200,
    )

    selected = select_text(article, fetched)

    assert selected.body_source == ArticleBodySource.FEED_SUMMARY
    assert "A summary of the event." in selected.text


def test_select_text_ignores_fetched_body_for_summary_only_source() -> None:
    article = _article(fetch_policy=SourceFetchPolicy.SUMMARY_ONLY)
    fetched = FetchResult(
        url=article.url,
        reason=FetchReason.OK,
        text="Full article body " * 40,
        http_status=200,
    )

    selected = select_text(article, fetched)

    assert selected.body_source == ArticleBodySource.FEED_SUMMARY


def test_select_text_reports_missing_text() -> None:
    article = _article(feed_summary=None)

    selected = select_text(article, None)

    assert selected.body_source is None
    assert selected.text == ""
    assert selected.input_quality == 0.1


def test_select_text_falls_back_when_fetch_is_short() -> None:
    article = _article()
    fetched = FetchResult(
        url=article.url,
        reason=FetchReason.SHORT,
        text="Too short.",
        http_status=200,
    )

    selected = select_text(article, fetched)

    assert selected.body_source == ArticleBodySource.FEED_SUMMARY


def test_to_label_payload_maps_enums_and_normalizes_time() -> None:
    extraction = ArticleLabelExtraction(
        index=0,
        is_event=True,
        article_type="breaking",
        event_form="incident",
        category="disaster",
        specificity=5,
        consequence=4,
        certainty="reported",
        fact="Fact text.",
        event_time=datetime(2026, 11, 18, 9, 0),
        locations=[{"name": "Coastal City", "country_code": "ex"}],
        entities=[{"name": "Coastal City", "kind": "location"}],
        scale_facts={"deaths": 12},
        severity=4,
        scope="city",
        confidence=0.9,
        evidence_quote="Fact text.",
    )

    payload = to_label_payload(extraction, input_hash="a" * 64)

    assert payload.article_type == ArticleType.BREAKING
    assert payload.event_form == EventForm.INCIDENT
    assert payload.category == ArticleCategory.DISASTER
    assert payload.certainty == ArticleCertainty.REPORTED
    assert payload.scope == EventScope.CITY
    assert payload.event_time is not None
    assert payload.event_time.tzinfo is not None
    assert payload.entities == [{"name": "Coastal City", "kind": "LOCATION"}]
    assert payload.locations == [{"name": "Coastal City", "country_code": "EX"}]
    assert payload.input_hash == "a" * 64


def test_label_input_hash_changes_with_body() -> None:
    article = _article()
    without_body = build_label_input(index=0, article=article, body=None)
    with_body = build_label_input(index=0, article=article, body="Body text.")

    assert label_input_hash(without_body) == label_input_hash(without_body)
    assert label_input_hash(without_body) != label_input_hash(with_body)


def test_build_text_hashes_returns_sixteen_char_hex() -> None:
    title_hash, body_hash = build_text_hashes(
        title="Earthquake strikes coastal city",
        text="Rescue teams searched collapsed buildings.",
    )

    assert title_hash is not None
    assert body_hash is not None
    assert len(title_hash) == 16
    assert len(body_hash) == 16

    _title, empty_body = build_text_hashes(title="Only a title", text="")
    assert empty_body is None


def test_build_embedding_text_uses_fact_entities_and_primary_location() -> None:
    payload = _payload(
        entities=[
            {"name": "Coastal City", "kind": "LOCATION"},
            {"name": "Emergency Service", "kind": "ORGANIZATION"},
        ],
        locations=[
            {"name": "Coastal City", "country_code": "EX"},
            {"name": "Example Country", "country_code": "EX"},
        ],
    )

    text = build_embedding_text(payload, title="Earthquake headline")

    assert "Earthquake headline" in text
    assert payload.fact is not None
    assert payload.fact in text
    assert "Emergency Service" in text
    assert "Example Country" not in text
