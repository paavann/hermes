import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hermes_api.db.models.event import Event
from hermes_api.db.models.event_tl import EventTl
from hermes_api.services.tl_service import TlService


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute.return_value = result_mock
    return session


@pytest.fixture
def dummy_event():
    return Event(
        id=uuid.uuid4(),
        ai_headline="Test Event",
        category="POLITICS",
        last_updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_ai_extraction():
    mock_extraction = MagicMock()
    mock_extraction.nodes = [
        MagicMock(
            date="2023-01-01",
            headline="Event 1",
            summary="Summary 1",
            location_name="Location A"
        ),
        MagicMock(
            date="2023-01-02",
            headline="Event 2",
            summary="Summary 2",
            location_name="Location B"
        )
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
@patch("hermes_api.services.tl_service.GeocodingService", autospec=True)
def test_first_generation(
    mock_geo_cls,
    mock_ai_cls,
    mock_fetch,
    mock_enum,
    mock_search,
    mock_session,
    dummy_event,
    mock_ai_extraction
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
        
        mock_geo = mock_geo_cls.return_value
        mock_geo.geocode = AsyncMock(return_value=MagicMock(latitude=10.0, longitude=20.0))

        mock_session.get.return_value = dummy_event
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock
        
        service = TlService(mock_session)
        response = await service.gen_tl(dummy_event.id)
        
        assert response.status == "READY"
        assert len(response.nodes) == 3
        assert len(response.edges) == 2
        assert response.nodes[0].latitude == 10.0
        assert response.nodes[0].longitude == 20.0
        assert response.nodes[-1].id == "current-event"
        assert response.nodes[-1].headline == dummy_event.ai_headline
    asyncio.run(run_test())


def test_second_click_returns_cache(mock_session, dummy_event):
    async def run_test():
        existing_tl = EventTl(
            event_id=dummy_event.id,
            status="READY",
            nodes=[{"id": "n1", "date": "2023-01-01", "headline": "H1", "summary": "S1", "location_name": "L1", "latitude": None, "longitude": None}],
            edges=[],
            tl_summary="Cached",
            generated_at=datetime.now(timezone.utc)
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing_tl
        mock_session.execute.return_value = result_mock
        mock_session.get.return_value = dummy_event

        service = TlService(mock_session)
        response = await service.gen_tl(dummy_event.id)
        
        assert response.status == "READY"
        assert response.tl_summary == "Cached"
        assert len(response.nodes) == 1
        mock_session.add.assert_not_called()
    asyncio.run(run_test())


def test_concurrent_generation_returns_generating(mock_session, dummy_event):
    async def run_test():
        existing_tl = EventTl(
            event_id=dummy_event.id,
            status="GENERATING",
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing_tl
        mock_session.execute.return_value = result_mock
        mock_session.get.return_value = dummy_event

        service = TlService(mock_session)
        response = await service.gen_tl(dummy_event.id)
        
        assert response.status == "GENERATING"
        mock_session.commit.assert_not_called()
    asyncio.run(run_test())


@patch("hermes_api.services.tl_service.search_wikipedia", new_callable=AsyncMock)
@patch("hermes_api.services.tl_service.AiService", autospec=True)
def test_no_wikipedia_match(mock_ai_cls, mock_search, mock_session, dummy_event):
    async def run_test():
        mock_ai = mock_ai_cls.return_value
        mock_ai.analyze_tl_context = AsyncMock(
            return_value=MagicMock(is_tl_worthy=True, wiki_search_query="Test Query")
        )
        mock_search.return_value = []
        mock_session.get.return_value = dummy_event
        
        service = TlService(mock_session)
        response = await service.gen_tl(dummy_event.id)
        
        assert response.status == "NO_CONTENT"
        mock_session.delete.assert_called_once()
    asyncio.run(run_test())


@patch("hermes_api.services.tl_service.search_wikipedia", new_callable=AsyncMock)
@patch("hermes_api.services.tl_service.enumerate_tl_pages", new_callable=AsyncMock)
@patch("hermes_api.services.tl_service.fetch_page_extracts", new_callable=AsyncMock)
@patch("hermes_api.services.tl_service.AiService", autospec=True)
@patch("hermes_api.services.tl_service.GeocodingService", autospec=True)
def test_force_refresh_regenerates(
    mock_geo_cls,
    mock_ai_cls,
    mock_fetch,
    mock_enum,
    mock_search,
    mock_session,
    dummy_event,
    mock_ai_extraction
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
        
        mock_geo = mock_geo_cls.return_value
        mock_geo.geocode = AsyncMock(return_value=None) 

        existing_tl = EventTl(
            event_id=dummy_event.id,
            status="READY",
            nodes=[],
            edges=[],
            tl_summary="Old Cached",
            generated_at=datetime.now(timezone.utc)
        )
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing_tl
        mock_session.execute.return_value = result_mock
        mock_session.get.return_value = dummy_event

        service = TlService(mock_session)
        response = await service.gen_tl(dummy_event.id, force_refresh=True)
        
        assert response.status == "READY"
        assert len(response.nodes) == 3
        assert response.nodes[0].latitude is None
        assert response.nodes[0].longitude is None
        assert response.nodes[-1].id == "current-event"
    asyncio.run(run_test())
