from datetime import UTC, datetime, timedelta

from hermes_db.enums import (
    CredibilityTier,
    GeopoliticalBloc,
    ImpactLevel,
)
from hermes_db.protocols import EventExtractionData, GeocodingData
from hermes_db.services.ranking import (
    CREDIBILITY_WEIGHTS,
    HALF_LIFE_HOURS,
    HOURLY_DECAY_FACTOR,
    IMPACT_MULTIPLIERS,
    SOURCE_BLOC_MAP,
    calculate_shannon_diversity,
    calculate_velocity,
    calculate_velocity_multiplier,
)


class DummyExtraction:
    headline: str = "Test"
    summary: str = "Summary"
    category: str = "WORLD"
    category_color: str | None = "#ff0000"
    location_name: str | None = "Paris"
    impact_level: str | None = "MAJOR"


class DummyGeocoding:
    latitude: float = 48.8566
    longitude: float = 2.3522


def test_protocols_conformance() -> None:
    extraction: EventExtractionData = DummyExtraction()
    assert extraction.headline == "Test"
    assert extraction.summary == "Summary"
    assert extraction.category == "WORLD"
    assert extraction.category_color == "#ff0000"
    assert extraction.location_name == "Paris"
    assert extraction.impact_level == "MAJOR"

    geocoding: GeocodingData = DummyGeocoding()
    assert geocoding.latitude == 48.8566
    assert geocoding.longitude == 2.3522


def test_ranking_constants() -> None:
    assert CREDIBILITY_WEIGHTS[CredibilityTier.TIER_1] == 3.0
    assert IMPACT_MULTIPLIERS[ImpactLevel.CRITICAL] == 2.0
    assert HALF_LIFE_HOURS == 18.0
    assert 0.0 < HOURLY_DECAY_FACTOR < 1.0
    assert SOURCE_BLOC_MAP["reuters-wire"] == GeopoliticalBloc.GLOBAL_WIRE


def test_ranking_diversity_and_velocity() -> None:
    assert calculate_shannon_diversity([]) == 1.0
    diversity = calculate_shannon_diversity(
        [GeopoliticalBloc.GLOBAL_WIRE, GeopoliticalBloc.EUROPE]
    )
    assert diversity > 1.0

    now = datetime.now(UTC)
    earlier = now - timedelta(hours=2)
    vel = calculate_velocity(6, earlier, now)
    assert vel == 3.0

    mult = calculate_velocity_multiplier(vel)
    assert mult > 1.0
