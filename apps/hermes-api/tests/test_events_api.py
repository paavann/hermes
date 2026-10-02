import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from hermes_db.enums import EventScope, EventStatus, EventTlStatus
from hermes_db.session import get_db
from hermes_api.main import app
from hermes_api.schemas.events import TlResponse


def test_get_events_with_scope_parameter():
    mock_session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session

    with (
        patch("hermes_api.main.init_db", new_callable=AsyncMock),
        patch("hermes_api.main.close_db", new_callable=AsyncMock),
        patch(
            "hermes_api.api.v1.events.EventService.get_events", new_callable=AsyncMock
        ) as mock_get_events,
    ):
        mock_get_events.return_value = []
        with TestClient(app) as client:
            response = client.get("/api/v1/events/?scope=GLOBAL&status=ACTIVE")
            assert response.status_code == 200
            assert response.json() == []
            mock_get_events.assert_awaited_once_with(
                status=EventStatus.ACTIVE,
                scope=EventScope.GLOBAL,
                limit=50,
            )

    app.dependency_overrides.clear()


def test_get_events_by_bbox_success():
    mock_session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session

    mock_row = MagicMock()
    mock_row.Event.id = uuid.uuid4()
    mock_row.Event.ai_headline = "Bbox Headline"
    mock_row.Event.category = "Politics"
    mock_row.Event.category_color = "#FF0000"
    mock_row.Event.location_name = "Berlin"
    mock_row.latitude = 52.52
    mock_row.longitude = 13.405
    mock_row.Event.trending_score = 4.5
    mock_row.Event.article_count = 3

    with (
        patch("hermes_api.main.init_db", new_callable=AsyncMock),
        patch("hermes_api.main.close_db", new_callable=AsyncMock),
        patch(
            "hermes_api.api.v1.events.EventService.get_events_by_bbox", new_callable=AsyncMock
        ) as mock_bbox,
    ):
        mock_bbox.return_value = [mock_row]
        with TestClient(app) as client:
            resp = client.get("/api/v1/events/bbox?north=60&south=40&east=20&west=0")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["ai_headline"] == "Bbox Headline"
            assert data[0]["latitude"] == 52.52
            assert data[0]["longitude"] == 13.405

    app.dependency_overrides.clear()


def test_get_events_by_bbox_invalid_lat():
    with TestClient(app) as client:
        # Latitude out of bounds (> 90)
        resp = client.get("/api/v1/events/bbox?north=120&south=40&east=20&west=0")
        assert resp.status_code == 422


def test_get_event_detail_success():
    mock_session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session

    event_id = uuid.uuid4()
    mock_detail = MagicMock()
    mock_detail.id = event_id
    mock_detail.ai_headline = "Detail Headline"
    mock_detail.ai_summary = "Detail Summary"
    mock_detail.category = "Politics"
    mock_detail.category_color = "#FF0000"
    mock_detail.location_name = "Paris"
    mock_detail.country_code = "FR"
    mock_detail.status = EventStatus.ACTIVE
    mock_detail.scope = EventScope.GLOBAL
    mock_detail.trending_score = 5.0
    mock_detail.article_count = 1
    mock_detail.last_updated_at = datetime.now(UTC)
    mock_detail.articles = []

    with (
        patch("hermes_api.main.init_db", new_callable=AsyncMock),
        patch("hermes_api.main.close_db", new_callable=AsyncMock),
        patch(
            "hermes_api.api.v1.events.EventService.get_event_by_id", new_callable=AsyncMock
        ) as mock_get_detail,
    ):
        mock_get_detail.return_value = mock_detail
        with TestClient(app) as client:
            resp = client.get(f"/api/v1/events/{event_id}")
            assert resp.status_code == 200
            assert resp.json()["id"] == str(event_id)
            assert resp.json()["ai_headline"] == "Detail Headline"

    app.dependency_overrides.clear()


def test_get_event_detail_not_found():
    mock_session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session

    event_id = uuid.uuid4()

    with (
        patch("hermes_api.main.init_db", new_callable=AsyncMock),
        patch("hermes_api.main.close_db", new_callable=AsyncMock),
        patch(
            "hermes_api.api.v1.events.EventService.get_event_by_id", new_callable=AsyncMock
        ) as mock_get_detail,
    ):
        mock_get_detail.return_value = None
        with TestClient(app) as client:
            resp = client.get(f"/api/v1/events/{event_id}")
            assert resp.status_code == 404

    app.dependency_overrides.clear()


def test_tl_endpoint_post():
    mock_session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session

    event_id = uuid.uuid4()
    mock_tl_resp = TlResponse(
        status=EventTlStatus.READY,
        nodes=[],
        edges=[],
        tl_summary="Test timeline",
    )

    with (
        patch("hermes_api.main.init_db", new_callable=AsyncMock),
        patch("hermes_api.main.close_db", new_callable=AsyncMock),
        patch(
            "hermes_api.services.tl_service.TlService.gen_tl", new_callable=AsyncMock
        ) as mock_gen,
    ):
        mock_gen.return_value = mock_tl_resp
        with TestClient(app) as client:
            resp = client.post(f"/api/v1/events/tl/{event_id}?force_refresh=true")
            assert resp.status_code == 200
            assert resp.json()["status"] == "READY"
            assert resp.json()["tl_summary"] == "Test timeline"
            mock_gen.assert_awaited_once_with(event_id, force_refresh=True)

    app.dependency_overrides.clear()
