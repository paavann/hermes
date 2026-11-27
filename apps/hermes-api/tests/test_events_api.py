import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from hermes_db.enums import (
    EventRelationshipType,
    EventScope,
    EventStatus,
    EventTlStatus,
    ImpactLevel,
    SelectionTier,
    VerificationStatus,
)
from hermes_db.services.event_relationship import (
    EventRelationshipView,
    MapRelationshipView,
)
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


def _mock_event_fields(event: MagicMock, *, event_id: uuid.UUID) -> None:
    event.id = event_id
    event.ai_headline = "Headline"
    event.ai_summary = "Summary"
    event.category = "Politics"
    event.category_color = "#FF0000"
    event.location_name = "Berlin"
    event.country_code = "DE"
    event.importance_score = 62.5
    event.score_breakdown = {"version": "score-v1", "score": 62.5}
    event.verification_status = VerificationStatus.CORROBORATED
    event.selection_tier = SelectionTier.PRIMARY
    event.impact_level = ImpactLevel.MAJOR
    event.scope = EventScope.COUNTRY
    event.status = EventStatus.ACTIVE
    event.event_time = datetime.now(UTC)
    event.article_count = 3
    event.source_count = 2
    event.family_count = 2
    event.independent_origin_count = 2
    event.actors = []
    event.thread_id = None
    event.thread = None
    event.thread_name = None
    event.first_reported_at = datetime.now(UTC)
    event.last_updated_at = datetime.now(UTC)


def test_get_events_by_bbox_success():
    mock_session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session

    mock_row = MagicMock()
    _mock_event_fields(mock_row.Event, event_id=uuid.uuid4())
    mock_row.Event.ai_headline = "Bbox Headline"
    mock_row.Event.location_name = "Gaza Strip"
    mock_row.Event.actors = [
        {
            "name": "Israel",
            "kind": "STATE",
            "role": "ACTOR",
            "location_name": "Israel",
            "country_code": "IL",
            "latitude": 31.0461,
            "longitude": 34.8516,
        }
    ]
    mock_row.latitude = 52.52
    mock_row.longitude = 13.405
    mock_row.thread_name = None

    with (
        patch("hermes_api.main.init_db", new_callable=AsyncMock),
        patch("hermes_api.main.close_db", new_callable=AsyncMock),
        patch(
            "hermes_api.api.v1.events.EventService.get_events_by_bbox",
            new_callable=AsyncMock,
        ) as mock_bbox,
        patch(
            "hermes_api.api.v1.events.EventService.relationship_counts",
            new_callable=AsyncMock,
        ) as mock_counts,
    ):
        mock_bbox.return_value = [mock_row]
        mock_counts.return_value = {mock_row.Event.id: 2}
        with TestClient(app) as client:
            resp = client.get("/api/v1/events/bbox?north=60&south=40&east=20&west=0")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["ai_headline"] == "Bbox Headline"
            assert data[0]["latitude"] == 52.52
            assert data[0]["longitude"] == 13.405
            assert data[0]["relationship_count"] == 2
            assert data[0]["actors"] == [
                {
                    "name": "Israel",
                    "kind": "STATE",
                    "role": "ACTOR",
                    "location_name": "Israel",
                    "country_code": "IL",
                    "latitude": 31.0461,
                    "longitude": 34.8516,
                }
            ]

    app.dependency_overrides.clear()


def test_get_events_by_bbox_invalid_lat():
    with (
        patch("hermes_api.main.init_db", new_callable=AsyncMock),
        patch("hermes_api.main.close_db", new_callable=AsyncMock),
        TestClient(app) as client,
    ):
        resp = client.get("/api/v1/events/bbox?north=120&south=40&east=20&west=0")
        assert resp.status_code == 422


def test_get_event_detail_success():
    mock_session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session

    event_id = uuid.uuid4()
    mock_detail = MagicMock()
    _mock_event_fields(mock_detail, event_id=event_id)
    mock_detail.ai_headline = "Detail Headline"
    mock_detail.ai_summary = "Detail Summary"
    mock_detail.location_name = "Paris"
    mock_detail.country_code = "FR"
    mock_detail.scope = EventScope.GLOBAL
    mock_detail.articles = []

    related_id = uuid.uuid4()
    rel_id = uuid.uuid4()
    rel_view = EventRelationshipView(
        id=rel_id,
        relationship_type=EventRelationshipType.REACTION,
        direction="INCOMING",
        confidence=0.92,
        rationale="Islamabad crowd gathered for the orbital docking.",
        related_event_id=related_id,
        related_headline="SUPARCO crowd celebrates docking",
        related_category="TECHNOLOGY",
        related_category_color="#00f0ff",
        related_location_name="Islamabad, Pakistan",
        related_latitude=33.6946,
        related_longitude=73.0646,
        related_importance_score=28.0,
        related_event_time=datetime.now(UTC),
    )

    with (
        patch("hermes_api.main.init_db", new_callable=AsyncMock),
        patch("hermes_api.main.close_db", new_callable=AsyncMock),
        patch(
            "hermes_api.api.v1.events.EventService.get_event_by_id",
            new_callable=AsyncMock,
        ) as mock_get_detail,
        patch(
            "hermes_api.api.v1.events.EventRelationshipService.relationships_for_event",
            new_callable=AsyncMock,
        ) as mock_rels,
    ):
        mock_get_detail.return_value = mock_detail
        mock_rels.return_value = [rel_view]
        with TestClient(app) as client:
            resp = client.get(f"/api/v1/events/{event_id}")
            assert resp.status_code == 200
            body = resp.json()
            assert body["id"] == str(event_id)
            assert body["ai_headline"] == "Detail Headline"
            assert body["relationship_count"] == 1
            assert len(body["relationships"]) == 1
            assert body["relationships"][0]["relationship_type"] == "REACTION"
            assert body["relationships"][0]["direction"] == "INCOMING"
            assert body["relationships"][0]["related_event_id"] == str(related_id)

    app.dependency_overrides.clear()


def test_get_event_detail_not_found():
    mock_session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session

    event_id = uuid.uuid4()

    with (
        patch("hermes_api.main.init_db", new_callable=AsyncMock),
        patch("hermes_api.main.close_db", new_callable=AsyncMock),
        patch(
            "hermes_api.api.v1.events.EventService.get_event_by_id",
            new_callable=AsyncMock,
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


def test_get_relationships_by_bbox_success():
    mock_session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session

    source_id = uuid.uuid4()
    target_id = uuid.uuid4()
    edge_id = uuid.uuid4()

    mock_row = MagicMock()
    _mock_event_fields(mock_row.Event, event_id=source_id)
    mock_edge = MapRelationshipView(
        id=edge_id,
        source_event_id=source_id,
        target_event_id=target_id,
        source_headline="Muhammad Zeeshan Ali boards China's Tiangong",
        source_category="SCIENCE",
        source_category_color="#a855f7",
        source_location_name="China",
        source_latitude=34.79,
        source_longitude=103.71,
        target_headline="SUPARCO hosts watch party in Islamabad",
        target_category="TECHNOLOGY",
        target_category_color="#00f0ff",
        target_location_name="Islamabad, Pakistan",
        target_latitude=33.6946,
        target_longitude=73.0646,
        relationship_type=EventRelationshipType.REACTION,
        confidence=0.91,
        rationale="Islamabad crowd gathered for the orbital docking.",
    )

    with (
        patch("hermes_api.main.init_db", new_callable=AsyncMock),
        patch("hermes_api.main.close_db", new_callable=AsyncMock),
        patch(
            "hermes_api.api.v1.events.EventService.get_events_by_bbox",
            new_callable=AsyncMock,
        ) as mock_bbox,
        patch(
            "hermes_api.api.v1.events.EventRelationshipService.relationships_for_event_ids",
            new_callable=AsyncMock,
        ) as mock_edges,
    ):
        mock_bbox.return_value = [mock_row]
        mock_edges.return_value = [mock_edge]
        with TestClient(app) as client:
            resp = client.get(
                "/api/v1/events/relationships?north=50&south=20&east=120&west=60"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["id"] == str(edge_id)
            assert data[0]["source_event_id"] == str(source_id)
            assert data[0]["target_event_id"] == str(target_id)
            assert data[0]["relationship_type"] == "REACTION"
            mock_edges.assert_awaited_once_with([source_id], limit=400)

    app.dependency_overrides.clear()


def test_get_relationships_by_bbox_empty_viewport():
    mock_session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session

    with (
        patch("hermes_api.main.init_db", new_callable=AsyncMock),
        patch("hermes_api.main.close_db", new_callable=AsyncMock),
        patch(
            "hermes_api.api.v1.events.EventService.get_events_by_bbox",
            new_callable=AsyncMock,
        ) as mock_bbox,
    ):
        mock_bbox.return_value = []
        with TestClient(app) as client:
            resp = client.get(
                "/api/v1/events/relationships?north=50&south=20&east=120&west=60"
            )
            assert resp.status_code == 200
            assert resp.json() == []

    app.dependency_overrides.clear()
