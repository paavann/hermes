from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from hermes_db.enums import EventScope, EventStatus
from hermes_db.session import get_db
from hermes_api.main import app


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
