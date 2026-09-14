"""Tests for the lineage persistence service."""

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from hermes_api.db.models.article import Article
from hermes_api.db.models.event import Event
from hermes_api.db.models.source import Source
from hermes_api.services.ai_service import TimelineEvent
from hermes_api.services.lineage_service import LineageService
from hermes_api.services.geocoding_service import GeocodingResult


def test_parse_timeline_date():
    mock_session = AsyncMock()
    service = LineageService(mock_session)
    
    # Test Full YYYY-MM-DD
    d1 = service._parse_timeline_date("2023-10-07")
    assert d1.year == 2023
    assert d1.month == 10
    assert d1.day == 7

    # Test YYYY-MM
    d2 = service._parse_timeline_date("2023-10")
    assert d2.year == 2023
    assert d2.month == 10
    assert d2.day == 1

    # Test YYYY
    d3 = service._parse_timeline_date("2023")
    assert d3.year == 2023
    assert d3.month == 1
    assert d3.day == 1

    # Test Empty / Error (falls back to now)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    d4 = service._parse_timeline_date("")
    assert d4.year == now.year
    d5 = service._parse_timeline_date("Invalid Format")
    assert d5.year == now.year


@patch("hermes_api.services.lineage_service.GeocodingService")
def test_persist_lineage_events(mock_geo_cls):
    mock_geo_instance = AsyncMock()
    mock_geo_cls.return_value = mock_geo_instance
    mock_session = AsyncMock()
    service = LineageService(mock_session)

    # 1. Setup mock source retrieval
    # _get_or_create_wikipedia_source calls session.execute, which returns a mock result
    mock_source = Source(id=uuid.uuid4(), name="Wikipedia")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_source
    mock_session.execute.return_value = mock_result

    # 2. Setup mock geocoding
    mock_geo_instance.geocode.return_value = GeocodingResult(
        display_name="Gaza City",
        latitude=31.5,
        longitude=34.4,
    )

    # 3. Execution
    target_event_id = uuid.uuid4()
    events = [
        TimelineEvent(
            date="2023-10-07",
            headline="Hamas attacks",
            summary="Attacks occur.",
            location_name="Gaza City"
        )
    ]
    
    result = asyncio.run(service.persist_lineage_events(
        target_event_id=target_event_id,
        events=events,
        page_title="Timeline of Gaza war"
    ))

    # 4. Assertions
    assert len(result) == 1
    event: Event = result[0]
    assert event.ai_headline == "Hamas attacks"
    assert event.category == "HISTORICAL"
    assert event.lineage_target_id == target_event_id
    assert event.location_name == "Gaza City"
    assert event.location == "SRID=4326;POINT(34.4 31.5)"
    assert event.first_reported_at.year == 2023
    assert event.first_reported_at.month == 10

    # Ensure session.add was called for both Event and Article
    adds = mock_session.add.call_args_list
    assert len(adds) == 2  # 1 event, 1 article (source was cached in scalar_one_or_none)
    
    article: Article = adds[1][0][0]
    assert isinstance(article, Article)
    assert article.source_id == mock_source.id
    assert "Timeline of Gaza war" in article.title
    assert "Timeline_of_Gaza_war" in article.url
    assert str(event.id) in article.url  # unique anchor
    assert article.published_at.year == 2023
