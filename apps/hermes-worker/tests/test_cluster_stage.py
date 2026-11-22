"""Tests for clustering helpers: impact mapping, locations, and prompt sides."""

import uuid
from datetime import UTC, datetime
from hermes_db.enums import (
    ArticleCategory,
    ArticleType,
    EventForm,
    EventScope,
    ImpactLevel,
)
from hermes_db.services import AssignableArticle, EventCandidate
from hermes_worker.jobs.stages.cluster import (
    _article_location,
    _article_side,
    _event_side,
    _headline,
    _impact_level,
    _merge_locations,
    _pair_hash,
    _primary_location,
)


NOW = datetime(2026, 11, 20, 12, 0, 0, tzinfo=UTC)


def _article(
    *,
    fact: str = "An explosion struck the central market.",
    severity: int | None = 4,
    locations: tuple[dict[str, object], ...] = (),
    entities: tuple[dict[str, object], ...] = (),
) -> AssignableArticle:
    return AssignableArticle(
        id=uuid.uuid4(),
        title="Market explosion",
        url="https://example.com/story",
        feed_summary=None,
        published_at=NOW,
        source_id=uuid.uuid4(),
        source_name="Example",
        source_slug="example",
        source_origin_group="example",
        family_id=None,
        embedding=None,
        embedding_model=None,
        fact=fact,
        event_time=NOW,
        article_type=ArticleType.BREAKING,
        category=ArticleCategory.CONFLICT,
        event_form=EventForm.INCIDENT,
        specificity=4,
        consequence=4,
        certainty=None,
        severity=severity,
        scope=EventScope.CITY,
        confidence=0.9,
        entities=entities,
        locations=locations,
    )


def _candidate(
    *,
    locations: tuple[dict[str, object], ...] = (),
    entities: frozenset[str] = frozenset(),
) -> EventCandidate:
    return EventCandidate(
        id=uuid.uuid4(),
        ai_headline="Explosion hits market",
        ai_summary="An explosion struck the central market.",
        category="CONFLICT",
        scope=EventScope.CITY,
        event_time=NOW,
        latest_published_at=NOW,
        country_code="UA",
        latitude=50.45,
        longitude=30.52,
        member_hash="hash",
        embedding=None,
        embedding_model=None,
        locations=locations,
        entities=entities,
        event_form=EventForm.INCIDENT,
    )


class TestHeadline:
    def test_keeps_short_fact_intact(self) -> None:
        assert _headline(_article(fact="Short fact.")) == "Short fact."

    def test_truncates_long_fact_with_ellipsis(self) -> None:
        headline = _headline(_article(fact="x" * 200))

        assert len(headline) == 120
        assert headline.endswith("...")


class TestImpactLevel:
    def test_maps_severity_to_impact(self) -> None:
        assert _impact_level(5) == ImpactLevel.CRITICAL
        assert _impact_level(4) == ImpactLevel.MAJOR
        assert _impact_level(3) == ImpactLevel.MODERATE
        assert _impact_level(2) == ImpactLevel.MINOR

    def test_defaults_to_moderate(self) -> None:
        assert _impact_level(None) == ImpactLevel.MODERATE


class TestLocations:
    def test_primary_location_normalizes_country_code(self) -> None:
        article = _article(
            locations=(
                {"name": "  ", "country_code": "UA"},
                {"name": " Kyiv ", "country_code": "ua"},
            )
        )

        assert _primary_location(article) == ("Kyiv", "UA")

    def test_primary_location_returns_none_without_locations(self) -> None:
        assert _primary_location(_article()) == (None, None)

    def test_article_location_returns_geo_location(self) -> None:
        article = _article(locations=({"name": "Kyiv", "country_code": "ua"},))

        location = _article_location(article)

        assert location is not None
        assert location.name == "Kyiv"
        assert location.country_code == "ua"

    def test_merge_locations_deduplicates_and_caps(self) -> None:
        merged = _merge_locations(
            [{"name": "Kyiv", "country_code": "ua"}],
            [
                {"name": " kyiv ", "country_code": "UA"},
                {"name": "Lviv", "country_code": "ua"},
                {"name": "Odesa", "country_code": "ua"},
                {"name": "Kharkiv", "country_code": "ua"},
            ],
        )

        assert [location["name"] for location in merged] == [
            "Kyiv",
            "Lviv",
            "Odesa",
        ]


class TestPromptSides:
    def test_article_side_uses_primary_location_and_entities(self) -> None:
        article = _article(
            locations=({"name": "Kyiv", "country_code": "UA"},),
            entities=({"name": "Mayor"}, {"name": "  "}, {"name": "Army"}),
        )

        side = _article_side(article)

        assert side.location == "Kyiv"
        assert side.entities == ["Mayor", "Army"]
        assert side.category == "CONFLICT"

    def test_event_side_uses_first_location_and_sorted_entities(self) -> None:
        candidate = _candidate(
            locations=({"name": "Kyiv"}, {"name": "Lviv"}),
            entities=frozenset({"mayor", "army"}),
        )

        side = _event_side(candidate)

        assert side.location == "Kyiv"
        assert side.entities == ["army", "mayor"]


class TestPairHash:
    def test_changes_when_member_hash_changes(self) -> None:
        import dataclasses

        article = _article()
        candidate = _candidate()
        baseline = _pair_hash(article.id, candidate, "v1")

        changed = dataclasses.replace(candidate, member_hash="new-hash")

        assert _pair_hash(article.id, changed, "v1") != baseline

    def test_changes_when_prompt_version_changes(self) -> None:
        article = _article()
        candidate = _candidate()

        assert _pair_hash(article.id, candidate, "v1") != _pair_hash(
            article.id, candidate, "v2"
        )
