"""Tests for description synthesis helpers and primary-location geocoding."""

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from hermes_ai import EventDescription, GeocodingResult
from hermes_ai.models.describe import DescribeImpact
from hermes_ai.models.labels import LabelLocation, LabelScope
from hermes_db.enums import EventScope, ImpactLevel
from hermes_db.services import MemberRecord
from hermes_worker.core.config import Settings
from hermes_worker.jobs.context import JobContext, LlmBudget, StageStats, WorkerIdentity
from hermes_worker.jobs.stages.describe import (
    MAX_HEADLINE_CHARS,
    MAX_SUMMARY_CHARS,
    _apply_description,
    _apply_fallback,
    _EventFacts,
    _geocode_primary,
    _member_locations,
    _one_per_family,
)


NOW = datetime(2026, 11, 20, 12, 0, 0, tzinfo=UTC)


def _member(
    *,
    article_id: uuid.UUID | None = None,
    family_id: uuid.UUID | None = None,
    published_at: datetime | None = NOW,
    fact: str | None = "An explosion struck the market.",
    locations: tuple[dict[str, object], ...] = (),
) -> MemberRecord:
    return MemberRecord(
        event_id=uuid.uuid4(),
        article_id=article_id or uuid.uuid4(),
        family_id=family_id,
        source_id=uuid.uuid4(),
        source_name="Example",
        source_origin_group="example",
        source_slug="example",
        source_credibility=None,
        published_at=published_at,
        embedding=None,
        embedding_model=None,
        input_quality=None,
        article_type=None,
        fact=fact,
        certainty=None,
        consequence=None,
        specificity=None,
        scale_facts=(),
        entities=(),
        locations=locations,
    )


def _description(**overrides: object) -> EventDescription:
    data: dict[str, object] = {
        "index": 0,
        "headline": "Explosion strikes central Kyiv market",
        "summary": "An explosion struck the central market in Kyiv, injuring several people.",
        "impact_level": DescribeImpact.MAJOR,
        "scope": LabelScope.CITY,
        "locations": [
            LabelLocation(name="Kyiv, Ukraine", country_code="ua"),
            LabelLocation(name="Ukraine", country_code="UA"),
        ],
    }
    data.update(overrides)
    return EventDescription(**data)


class TestOnePerFamily:
    def test_keeps_earliest_member_per_family(self) -> None:
        family = uuid.uuid4()
        later = _member(family_id=family, published_at=NOW)
        earlier = _member(family_id=family, published_at=NOW.replace(hour=8))
        standalone = _member()

        selected = _one_per_family([later, earlier, standalone])

        assert selected == [earlier, standalone]

    def test_uses_article_id_when_family_is_missing(self) -> None:
        first = _member()
        second = _member()

        assert _one_per_family([first, second]) == [first, second]


class TestApplyDescription:
    def test_sets_headline_summary_impact_scope_and_locations(self) -> None:
        event = MagicMock()
        event.locations = []
        event.country_code = None

        _apply_description(event, _description())

        assert event.ai_headline == "Explosion strikes central Kyiv market"
        assert event.ai_summary.startswith("An explosion struck")
        assert event.impact_level == ImpactLevel.MAJOR
        assert event.scope == EventScope.CITY
        assert event.location_name == "Kyiv, Ukraine"
        assert event.country_code == "UA"
        assert event.locations[0] == {
            "name": "Kyiv, Ukraine",
            "country_code": "UA",
        }

    def test_truncates_overlong_text(self) -> None:
        event = MagicMock()
        event.locations = []
        description = _description(
            headline="H" * MAX_HEADLINE_CHARS,
            summary="S" * MAX_SUMMARY_CHARS,
        )

        _apply_description(event, description)

        assert len(event.ai_headline) <= MAX_HEADLINE_CHARS
        assert len(event.ai_summary) <= MAX_SUMMARY_CHARS

    def test_keeps_previous_location_when_description_has_none(self) -> None:
        event = MagicMock()
        event.location_name = "Kyiv"
        event.country_code = "UA"
        event.locations = [{"name": "Kyiv", "country_code": "UA"}]

        _apply_description(event, _description(locations=[]))

        assert event.location_name == "Kyiv"
        assert event.locations == []


class TestApplyFallback:
    def test_uses_member_facts_and_locations(self) -> None:
        event = MagicMock()
        event.ai_headline = "Old headline"
        event.locations = []
        event.country_code = None
        item = _EventFacts(
            event=event,
            members=(
                _member(
                    fact="An explosion struck the market.",
                    locations=({"name": "Kyiv", "country_code": "ua"},),
                ),
            ),
            hash="hash",
        )

        _apply_fallback(event, item)

        assert event.ai_headline == "An explosion struck the market."
        assert event.ai_summary == "An explosion struck the market."
        assert event.location_name == "Kyiv"
        assert event.country_code == "UA"

    def test_keeps_existing_headline_without_facts(self) -> None:
        event = MagicMock()
        event.ai_headline = "Existing headline"
        event.locations = []
        item = _EventFacts(event=event, members=(), hash="hash")

        _apply_fallback(event, item)

        assert event.ai_headline == "Existing headline"


class TestMemberLocations:
    def test_deduplicates_and_caps_at_three(self) -> None:
        members = (
            _member(
                locations=(
                    {"name": "Kyiv", "country_code": "ua"},
                    {"name": " kyiv ", "country_code": "UA"},
                    {"name": "Lviv", "country_code": "ua"},
                    {"name": "Odesa", "country_code": "ua"},
                    {"name": "Kharkiv", "country_code": "ua"},
                )
            ),
        )

        locations = _member_locations(members)

        assert [location["name"] for location in locations] == [
            "Kyiv",
            "Lviv",
            "Odesa",
        ]

    def test_skips_blank_names(self) -> None:
        members = (_member(locations=({"name": "  "}, {"name": "Kyiv"})),)

        assert _member_locations(members) == [{"name": "Kyiv", "country_code": None}]


def _context(geocoder: object) -> JobContext:
    return JobContext(
        settings=Settings(_env_file=None, DB_PASSWORD="worker-secret-pass"),
        engine=MagicMock(),
        session_factory=MagicMock(),
        identity=WorkerIdentity(hostname="host", pid=1),
        budget=LlmBudget(max_llm_calls=1),
        geocoder=geocoder,  # type: ignore[arg-type]
    )


class TestGeocodePrimary:
    def test_sets_point_on_success(self) -> None:
        async def _test() -> None:
            geocoder = MagicMock()
            geocoder.geocode = AsyncMock(
                return_value=GeocodingResult(
                    latitude=50.45,
                    longitude=30.52,
                    display_name="Kyiv, Ukraine",
                )
            )
            ctx = _context(geocoder)
            event = MagicMock()
            event.location_name = "Kyiv, Ukraine"
            stats = StageStats()

            await _geocode_primary(ctx, event, stats)

            assert event.location == "SRID=4326;POINT(30.52 50.45)"
            assert stats.counters == {"geocoded": 1}

        asyncio.run(_test())

    def test_clears_point_on_geocode_miss(self) -> None:
        async def _test() -> None:
            geocoder = MagicMock()
            geocoder.geocode = AsyncMock(return_value=None)
            ctx = _context(geocoder)
            event = MagicMock()
            event.location_name = "Nowhere"
            event.location = "SRID=4326;POINT(1 1)"
            stats = StageStats()

            await _geocode_primary(ctx, event, stats)

            assert event.location is None
            assert stats.counters == {"geocode_miss": 1}

        asyncio.run(_test())

    def test_clears_point_when_name_is_empty(self) -> None:
        async def _test() -> None:
            geocoder = MagicMock()
            geocoder.geocode = AsyncMock()
            ctx = _context(geocoder)
            event = MagicMock()
            event.location_name = None
            event.location = "SRID=4326;POINT(1 1)"
            stats = StageStats()

            await _geocode_primary(ctx, event, stats)

            assert event.location is None
            geocoder.geocode.assert_not_awaited()
            assert stats.counters == {}

        asyncio.run(_test())
