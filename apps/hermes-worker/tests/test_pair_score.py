"""Unit tests for article→event and event→event pair scoring."""

import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hermes_db.enums import (
    ArticleCategory,
    ArticleType,
    EventForm,
    EventScope,
    EventStatus,
)
from hermes_db.services import AssignableArticle, EventCandidate, EventPairState
from hermes_worker.jobs.pair_score import (
    AUTO_ATTACH_THRESHOLD,
    LLM_BAND_THRESHOLD,
    GeoLocation,
    PairScore,
    haversine_meters,
    normalize_entities,
    score_event_pair,
    score_pair,
)


NOW = datetime(2026, 11, 20, 12, 0, 0, tzinfo=UTC)
EMBEDDING_MODEL = "test-embed"


def _article(
    *,
    event_form: EventForm = EventForm.INCIDENT,
    scope: EventScope = EventScope.CITY,
    published_at: datetime = NOW,
    event_time: datetime | None = None,
    entities: tuple[dict[str, object], ...] = (),
    embedding: tuple[float, ...] | None = None,
    embedding_model: str | None = EMBEDDING_MODEL,
    fact: str = "An explosion struck the market.",
) -> AssignableArticle:
    return AssignableArticle(
        id=uuid.uuid4(),
        title="Market explosion",
        url="https://example.com/story",
        feed_summary=None,
        published_at=published_at,
        source_id=uuid.uuid4(),
        source_name="Example",
        source_slug="example",
        source_origin_group="example",
        family_id=None,
        embedding=embedding,
        embedding_model=embedding_model,
        fact=fact,
        event_time=event_time,
        article_type=ArticleType.BREAKING,
        category=ArticleCategory.CONFLICT,
        event_form=event_form,
        specificity=4,
        consequence=4,
        certainty=None,
        severity=4,
        scope=scope,
        confidence=0.9,
        entities=entities,
        locations=(),
    )


def _candidate(
    *,
    event_form: EventForm = EventForm.INCIDENT,
    scope: EventScope = EventScope.CITY,
    event_time: datetime = NOW,
    entities: frozenset[str] = frozenset(),
    embedding: tuple[float, ...] | None = None,
    embedding_model: str | None = EMBEDDING_MODEL,
    country_code: str | None = "UA",
    locations: tuple[dict[str, object], ...] = (),
    latitude: float | None = None,
    longitude: float | None = None,
    headline: str = "Explosion hits market",
    summary: str | None = "An explosion struck the central market.",
) -> EventCandidate:
    return EventCandidate(
        id=uuid.uuid4(),
        ai_headline=headline,
        ai_summary=summary,
        category="CONFLICT",
        scope=scope,
        event_time=event_time,
        latest_published_at=event_time,
        country_code=country_code,
        latitude=latitude,
        longitude=longitude,
        member_hash="hash",
        embedding=embedding,
        embedding_model=embedding_model,
        locations=locations,
        entities=entities,
        event_form=event_form,
    )


def _event_state(
    *,
    event_time: datetime = NOW,
    embedding: tuple[float, ...] | None = None,
    embedding_model: str | None = EMBEDDING_MODEL,
    country_code: str | None = "UA",
    latitude: float | None = 50.45,
    longitude: float | None = 30.52,
    location_name: str | None = "Kyiv",
    category: str = "CONFLICT",
    scope: EventScope = EventScope.CITY,
) -> EventPairState:
    return EventPairState(
        id=uuid.uuid4(),
        ai_headline="Explosion hits market",
        ai_summary="An explosion struck the central market.",
        category=category,
        event_time=event_time,
        latest_published_at=event_time,
        first_reported_at=event_time,
        country_code=country_code,
        location_name=location_name,
        latitude=latitude,
        longitude=longitude,
        embedding=embedding,
        embedding_model=embedding_model,
        member_hash="hash",
        article_count=2,
        thread_id=None,
        status=EventStatus.ACTIVE,
        scope=scope,
    )


def test_haversine_zero_for_identical_points() -> None:
    assert haversine_meters(50.0, 30.0, 50.0, 30.0) == 0.0


def test_haversine_known_distance() -> None:
    # Kyiv → Lviv is roughly 470 km.
    distance = haversine_meters(50.4501, 30.5234, 49.8397, 24.0297)
    assert 440_000 < distance < 500_000


def test_normalize_entities_handles_strings_dicts_and_duplicates() -> None:
    entities = normalize_entities(
        [
            {"name": "The Ministry of Defense"},
            "ministry of defense",
            {"name": "  Kyiv  "},
            {"bad": "shape"},
            42,
        ]
    )

    assert entities == frozenset({"ministry of defense", "kyiv"})


def test_normalize_entities_returns_empty_for_non_sequence() -> None:
    assert normalize_entities(None) == frozenset()
    assert normalize_entities("not-a-list") == frozenset()


def test_pair_score_band_mapping() -> None:
    assert PairScore(score=AUTO_ATTACH_THRESHOLD, components={}).band == "auto"
    assert PairScore(score=LLM_BAND_THRESHOLD, components={}).band == "llm"
    assert PairScore(score=0.1, components={}).band == "separate"
    assert PairScore(score=0.99, components={}, veto="entities").band == "separate"


def test_article_pair_auto_attach_for_identical_story() -> None:
    embedding = tuple([0.5] * 8)
    article = _article(
        entities=({"name": "Kyiv"},),
        embedding=embedding,
        event_time=NOW,
    )
    candidate = _candidate(
        entities=frozenset({"kyiv"}),
        embedding=embedding,
        latitude=50.45,
        longitude=30.52,
        locations=(
            {
                "name": "Kyiv",
                "country_code": "UA",
                "latitude": 50.45,
                "longitude": 30.52,
            },
        ),
    )

    result = score_pair(
        article,
        candidate,
        article_location=GeoLocation(
            name="Kyiv", country_code="UA", latitude=50.45, longitude=30.52
        ),
    )

    assert result.veto is None
    assert result.score >= AUTO_ATTACH_THRESHOLD
    assert result.band == "auto"
    assert result.components["embedding"] == 1.0
    assert result.components["entities"] == 1.0
    assert result.components["location"] == 1.0


def test_article_pair_vetoes_incompatible_forms() -> None:
    result = score_pair(
        _article(event_form=EventForm.INCIDENT),
        _candidate(event_form=EventForm.PLANNED_EVENT),
        article_location=None,
    )

    assert result.veto == "event_form"
    assert result.score == 0.0


def test_article_pair_vetoes_time_window_beyond_seven_days() -> None:
    result = score_pair(
        _article(published_at=NOW - timedelta(days=9)),
        _candidate(event_time=NOW),
        article_location=None,
    )

    assert result.veto == "time_window"


def test_article_pair_vetoes_disjoint_entities() -> None:
    result = score_pair(
        _article(entities=({"name": "Alpha"},)),
        _candidate(entities=frozenset({"beta"})),
        article_location=None,
    )

    assert result.veto == "entities"


def test_article_pair_vetoes_distant_local_locations() -> None:
    article = _article(scope=EventScope.CITY)
    candidate = _candidate(
        scope=EventScope.CITY,
        latitude=52.52,
        longitude=13.405,
        locations=(
            {
                "name": "Berlin",
                "country_code": "DE",
                "latitude": 52.52,
                "longitude": 13.405,
            },
        ),
    )

    result = score_pair(
        article,
        candidate,
        article_location=GeoLocation(
            name="Kyiv", country_code="UA", latitude=50.45, longitude=30.52
        ),
    )

    assert result.veto == "location"


def test_article_pair_scores_partial_match_in_llm_band() -> None:
    article = _article(
        entities=({"name": "Kyiv"}, {"name": "Ministry"}),
        embedding=tuple([1.0, 0.0] * 4),
        event_time=NOW - timedelta(hours=20),
    )
    candidate = _candidate(
        entities=frozenset({"kyiv", "mayor", "council"}),
        embedding=tuple([0.8, 0.2] * 4),
        event_time=NOW,
        latitude=50.45,
        longitude=30.52,
        locations=(
            {
                "name": "Kyiv",
                "country_code": "UA",
                "latitude": 50.45,
                "longitude": 30.52,
            },
        ),
    )

    result = score_pair(
        article,
        candidate,
        article_location=GeoLocation(
            name="Kyiv", country_code="UA", latitude=50.45, longitude=30.52
        ),
    )

    assert result.veto is None
    assert 0.60 <= result.score < 0.80


def test_article_pair_ignores_embedding_from_other_model() -> None:
    article = _article(embedding=(1.0, 0.0), embedding_model="model-a")
    candidate = _candidate(embedding=(1.0, 0.0), embedding_model="model-b")

    result = score_pair(article, candidate, article_location=None)

    assert result.components["embedding"] == 0.0


def test_event_pair_auto_merge_for_duplicate_events() -> None:
    embedding = tuple([0.4] * 8)
    left = _event_state(embedding=embedding)
    right = _event_state(embedding=embedding)

    result = score_event_pair(
        left,
        right,
        left_entities=frozenset({"kyiv"}),
        right_entities=frozenset({"kyiv"}),
        shared_families=2,
    )

    assert result.veto is None
    assert result.score >= 0.92
    assert result.band == "auto"


def test_event_pair_vetoes_different_countries() -> None:
    result = score_event_pair(
        _event_state(country_code="UA"),
        _event_state(country_code="PL"),
        left_entities=frozenset(),
        right_entities=frozenset(),
        shared_families=0,
    )

    assert result.veto == "location"


def test_event_pair_vetoes_distant_coordinates() -> None:
    result = score_event_pair(
        _event_state(latitude=50.45, longitude=30.52),
        _event_state(latitude=52.52, longitude=13.405),
        left_entities=frozenset(),
        right_entities=frozenset(),
        shared_families=0,
    )

    assert result.veto == "location"


def test_event_pair_vetoes_old_pairs() -> None:
    result = score_event_pair(
        _event_state(event_time=NOW - timedelta(days=8)),
        _event_state(event_time=NOW),
        left_entities=frozenset(),
        right_entities=frozenset(),
        shared_families=0,
    )

    assert result.veto == "time_window"


def test_event_pair_vetoes_disjoint_entities() -> None:
    result = score_event_pair(
        _event_state(),
        _event_state(),
        left_entities=frozenset({"alpha"}),
        right_entities=frozenset({"beta"}),
        shared_families=0,
    )

    assert result.veto == "entities"


def test_event_pair_gray_band_requires_llm() -> None:
    left = _event_state(
        embedding=(1.0, 0.0) * 4,
        location_name="Kyiv",
        latitude=50.45,
        longitude=30.52,
    )
    right = _event_state(
        embedding=(0.75, 0.6614) * 4,
        location_name="Kyiv",
        latitude=50.45,
        longitude=30.52,
    )

    result = score_event_pair(
        left,
        right,
        left_entities=frozenset({"kyiv"}),
        right_entities=frozenset({"kyiv"}),
        shared_families=2,
    )

    assert result.veto is None
    assert 0.85 <= result.score < 0.90
    assert result.band == "llm"


def test_article_pair_matches_partial_person_name_variants() -> None:
    embedding = tuple([0.5] * 8)
    article = _article(
        entities=({"name": "Muhammad Zeeshan Ali"}, {"name": "Tiangong"}),
        embedding=embedding,
        event_time=NOW,
    )
    candidate = _candidate(
        entities=frozenset({"zeeshan ali", "tiangong"}),
        embedding=embedding,
        country_code="CN",
        latitude=34.79,
        longitude=103.71,
        locations=({"name": "China", "country_code": "CN"},),
    )

    result = score_pair(
        article,
        candidate,
        article_location=GeoLocation(name="China", country_code="CN"),
    )

    assert result.veto is None
    assert result.components["entities"] > 0.7
    assert result.band == "auto"


def test_high_cosine_bypasses_disjoint_entity_veto() -> None:
    embedding = tuple([0.6] * 8)
    article = _article(
        entities=({"name": "Tiangong"},),
        embedding=embedding,
    )
    candidate = _candidate(
        entities=frozenset({"china space station"}),
        embedding=embedding,
    )

    result = score_pair(article, candidate, article_location=None)

    assert result.veto is None
    assert result.components["embedding"] == 1.0


def test_event_pair_allows_country_centroid_and_city_in_same_country() -> None:
    embedding = tuple([0.5] * 8)
    left = _event_state(
        country_code="CN",
        location_name="China",
        latitude=34.79,
        longitude=103.71,
        category="SCIENCE",
        scope=EventScope.COUNTRY,
        embedding=embedding,
    )
    right = _event_state(
        country_code="CN",
        location_name="Beijing, China",
        latitude=39.9042,
        longitude=116.4074,
        category="TECHNOLOGY",
        scope=EventScope.CITY,
        embedding=embedding,
    )

    result = score_event_pair(
        left,
        right,
        left_entities=frozenset({"muhammad zeeshan ali", "tiangong"}),
        right_entities=frozenset({"zeeshan ali", "china"}),
        shared_families=0,
    )

    assert result.veto is None
    assert result.components["location"] == 0.6
    assert result.score >= 0.74
    assert result.band == "llm"


def test_event_pair_auto_merges_without_shared_families() -> None:
    embedding = tuple([0.5] * 8)
    left = _event_state(
        country_code="CN",
        location_name="China",
        latitude=34.79,
        longitude=103.71,
        category="SCIENCE",
        scope=EventScope.COUNTRY,
        embedding=embedding,
    )
    right = _event_state(
        country_code="CN",
        location_name="China",
        latitude=34.79,
        longitude=103.71,
        category="SCIENCE",
        scope=EventScope.COUNTRY,
        embedding=embedding,
    )

    result = score_event_pair(
        left,
        right,
        left_entities=frozenset({"tiangong"}),
        right_entities=frozenset({"tiangong"}),
        shared_families=0,
    )

    assert result.score == 1.0
    assert result.band == "auto"


def test_event_pair_falls_back_to_headline_entities_when_side_empty() -> None:
    left = replace(
        _event_state(
            country_code="CN",
            location_name="China",
            latitude=34.54,
            longitude=108.92,
            category="SCIENCE",
            scope=EventScope.GLOBAL,
            event_time=NOW - timedelta(hours=22),
            embedding=(1.0, 0.0, 0.0, 0.0),
        ),
        ai_headline="Muhammad Zeeshan Ali boards China's Tiangong",
    )
    right = replace(
        _event_state(
            country_code="CN",
            location_name="China",
            latitude=34.54,
            longitude=108.92,
            category="TECHNOLOGY",
            scope=EventScope.COUNTRY,
            event_time=NOW,
            embedding=(0.8415, 0.5403, 0.0, 0.0),
        ),
        ai_headline=(
            "Zeeshan Ali makes history as the first foreign national "
            "to board China’s space station."
        ),
    )

    result = score_event_pair(
        left,
        right,
        left_entities=frozenset(),
        right_entities=frozenset({"zeeshan ali", "space station", "china"}),
        shared_families=0,
    )

    assert result.veto is None
    assert result.components["entities"] > 0.5
    assert result.score >= 0.74
    assert result.band == "llm"
