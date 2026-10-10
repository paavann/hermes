import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from hermes_ai import GeocodingService
from hermes_db.enums import EventTlStatus
from hermes_db.models import Event, EventTl
from hermes_db.services.tl import EventTlService
from hermes_api.services.tl_service import TlService


@pytest.fixture
def dummy_event():
    evt = MagicMock(spec=Event)
    evt.id = uuid.uuid4()
    evt.ai_headline = "Test Event"
    evt.ai_summary = "Test summary"
    evt.category = "POLITICS"
    evt.category_color = "#FF0000"
    evt.location_name = "Location C"
    evt.last_updated_at = datetime.now(UTC)
    return evt


@pytest.fixture
def mock_tl_db():
    db = AsyncMock(spec=EventTlService)
    db.get_event = AsyncMock()
    db.get_tl = AsyncMock()
    db.create_tl = AsyncMock()
    db.update_tl_status = AsyncMock()
    db.delete_tl = AsyncMock()
    db.get_event_coordinates = AsyncMock(return_value=(10.0, 20.0))

    async def fake_save(
        tl,
        nodes,
        edges,
        tl_summary,
        wikipedia_title=None,
        page_count=0,
        node_count=0,
        status=EventTlStatus.READY,
    ):
        tl.nodes = nodes
        tl.edges = edges
        tl.tl_summary = tl_summary
        tl.status = status

    db.save_generated_tl = AsyncMock(side_effect=fake_save)
    return db


@pytest.fixture
def mock_geocoding():
    geo = AsyncMock(spec=GeocodingService)
    geo.geocode = AsyncMock()
    return geo


@pytest.fixture
def mock_ai_extraction():
    mock_extraction = MagicMock()
    mock_extraction.nodes = [
        MagicMock(
            date="2023-01-01",
            headline="Event 1",
            summary="Summary 1",
            location_name="Location A",
        ),
        MagicMock(
            date="2023-01-02",
            headline="Event 2",
            summary="Summary 2",
            location_name="Location B",
        ),
    ]
    mock_extraction.edges = [
        MagicMock(source_index=0, target_index=1, relationship="triggered")
    ]
    mock_extraction.tl_summary = "Topic summary."
    return mock_extraction


@patch("hermes_api.services.tl_service.search_wikipedia", new_callable=AsyncMock)
@patch("hermes_api.services.tl_service.enumerate_tl_pages", new_callable=AsyncMock)
@patch("hermes_api.services.tl_service.fetch_page_extracts", new_callable=AsyncMock)
@patch("hermes_api.services.tl_service.AiService", autospec=True)
def test_first_generation(
    mock_ai_cls,
    mock_fetch,
    mock_enum,
    mock_search,
    mock_tl_db,
    mock_geocoding,
    dummy_event,
    mock_ai_extraction,
):
    async def run_test():
        mock_search.return_value = ["Timeline of Test"]
        mock_enum.return_value = ["Timeline of Test"]
        mock_fetch.return_value = {"Timeline of Test": "Some prose."}

        mock_ai = mock_ai_cls.return_value
        mock_ai.analyze_tl_context = AsyncMock(
            return_value=MagicMock(is_tl_worthy=True, wiki_search_query="Test Query")
        )
        mock_ai.extract_tl = AsyncMock(return_value=mock_ai_extraction)

        mock_geocoding.geocode.return_value = MagicMock(latitude=10.0, longitude=20.0)

        mock_tl_db.get_event.return_value = dummy_event
        mock_tl_db.get_tl.return_value = None

        new_tl = EventTl(
            id=uuid.uuid4(),
            event_id=dummy_event.id,
            status=EventTlStatus.GENERATING,
            nodes=[],
            edges=[],
            tl_summary="",
            generated_at=datetime.now(UTC),
        )
        mock_tl_db.create_tl.return_value = new_tl

        service = TlService(tl_db=mock_tl_db, geocoding=mock_geocoding)
        # Patch service's internal _ai to our mock
        service._ai = mock_ai

        response = await service.gen_tl(dummy_event.id)

        assert response.status == EventTlStatus.READY
        assert len(response.nodes) == 3
        assert len(response.edges) == 2
        assert response.nodes[0].latitude == 10.0
        assert response.nodes[0].longitude == 20.0
        assert response.nodes[-1].id == "current-event"
        assert response.nodes[-1].headline == dummy_event.ai_headline

    asyncio.run(run_test())


def test_second_click_returns_cache(mock_tl_db, mock_geocoding, dummy_event):
    async def run_test():
        existing_tl = EventTl(
            id=uuid.uuid4(),
            event_id=dummy_event.id,
            status=EventTlStatus.READY,
            nodes=[
                {
                    "id": "n1",
                    "date": "2023-01-01",
                    "headline": "H1",
                    "summary": "S1",
                    "location_name": "L1",
                    "latitude": None,
                    "longitude": None,
                }
            ],
            edges=[],
            tl_summary="Cached",
            generated_at=datetime.now(UTC),
        )
        mock_tl_db.get_event.return_value = dummy_event
        mock_tl_db.get_tl.return_value = existing_tl

        service = TlService(tl_db=mock_tl_db, geocoding=mock_geocoding)
        response = await service.gen_tl(dummy_event.id)

        assert response.status == EventTlStatus.READY
        assert response.tl_summary == "Cached"
        assert len(response.nodes) == 1
        mock_tl_db.create_tl.assert_not_called()

    asyncio.run(run_test())


def test_concurrent_generation_returns_generating(mock_tl_db, mock_geocoding, dummy_event):
    async def run_test():
        existing_tl = EventTl(
            id=uuid.uuid4(),
            event_id=dummy_event.id,
            status=EventTlStatus.GENERATING,
            nodes=[],
            edges=[],
            tl_summary="",
        )
        mock_tl_db.get_event.return_value = dummy_event
        mock_tl_db.get_tl.return_value = existing_tl

        service = TlService(tl_db=mock_tl_db, geocoding=mock_geocoding)
        response = await service.gen_tl(dummy_event.id)

        assert response.status == EventTlStatus.GENERATING
        mock_tl_db.save_generated_tl.assert_not_called()

    asyncio.run(run_test())


@patch("hermes_api.services.tl_service.search_wikipedia", new_callable=AsyncMock)
@patch("hermes_api.services.tl_service.AiService", autospec=True)
def test_no_wikipedia_match(mock_ai_cls, mock_search, mock_tl_db, mock_geocoding, dummy_event):
    async def run_test():
        mock_ai = mock_ai_cls.return_value
        mock_ai.analyze_tl_context = AsyncMock(
            return_value=MagicMock(is_tl_worthy=True, wiki_search_query="Test Query")
        )
        mock_search.return_value = []
        mock_tl_db.get_event.return_value = dummy_event
        mock_tl_db.get_tl.return_value = None

        new_tl = EventTl(
            id=uuid.uuid4(),
            event_id=dummy_event.id,
            status=EventTlStatus.GENERATING,
            nodes=[],
            edges=[],
            tl_summary="",
        )
        mock_tl_db.create_tl.return_value = new_tl

        service = TlService(tl_db=mock_tl_db, geocoding=mock_geocoding)
        service._ai = mock_ai

        response = await service.gen_tl(dummy_event.id)

        assert response.status == EventTlStatus.NO_CONTENT
        mock_tl_db.delete_tl.assert_awaited_once_with(new_tl)

    asyncio.run(run_test())


@patch("hermes_api.services.tl_service.search_wikipedia", new_callable=AsyncMock)
@patch("hermes_api.services.tl_service.enumerate_tl_pages", new_callable=AsyncMock)
@patch("hermes_api.services.tl_service.fetch_page_extracts", new_callable=AsyncMock)
@patch("hermes_api.services.tl_service.AiService", autospec=True)
def test_force_refresh_regenerates(
    mock_ai_cls,
    mock_fetch,
    mock_enum,
    mock_search,
    mock_tl_db,
    mock_geocoding,
    dummy_event,
    mock_ai_extraction,
):
    async def run_test():
        mock_search.return_value = ["Timeline of Test"]
        mock_enum.return_value = ["Timeline of Test"]
        mock_fetch.return_value = {"Timeline of Test": "Regenerated prose."}

        mock_ai = mock_ai_cls.return_value
        mock_ai.analyze_tl_context = AsyncMock(
            return_value=MagicMock(is_tl_worthy=True, wiki_search_query="Test Query")
        )
        mock_ai.extract_tl = AsyncMock(return_value=mock_ai_extraction)

        mock_geocoding.geocode.return_value = None

        existing_tl = EventTl(
            id=uuid.uuid4(),
            event_id=dummy_event.id,
            status=EventTlStatus.READY,
            nodes=[],
            edges=[],
            tl_summary="Old Cached",
            generated_at=datetime.now(UTC),
        )
        mock_tl_db.get_event.return_value = dummy_event
        mock_tl_db.get_tl.return_value = existing_tl
        mock_tl_db.get_event_coordinates.return_value = (None, None)

        service = TlService(tl_db=mock_tl_db, geocoding=mock_geocoding)
        service._ai = mock_ai

        response = await service.gen_tl(dummy_event.id, force_refresh=True)

        assert response.status == EventTlStatus.READY
        assert len(response.nodes) == 3
        assert response.nodes[0].latitude is None
        assert response.nodes[0].longitude is None
        assert response.nodes[-1].id == "current-event"

    asyncio.run(run_test())
