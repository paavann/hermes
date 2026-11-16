import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from hermes_worker.core.config import Settings
from hermes_worker.services.lifecycle import run_lifecycle


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "DB_PASSWORD": "worker-secret-pass",
        "EVENT_STALE_HOURS": 12,
        "EVENT_ARCHIVE_HOURS": 36,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def test_run_lifecycle_executes_transitions() -> None:
    async def _test() -> None:
        mock_event_service = AsyncMock()
        mock_event_service.run_lifecycle_transitions.return_value = {
            "decayed_events": 10,
            "stale_events": 2,
            "archived_events": 1,
        }

        with (
            patch(
                "hermes_worker.services.lifecycle.AsyncSessionLocal"
            ) as mock_session_cls,
            patch(
                "hermes_worker.services.lifecycle.EventService",
                return_value=mock_event_service,
            ) as mock_service_cls,
        ):
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            stats = await run_lifecycle(_settings())

            assert stats["decayed_events"] == 10
            mock_service_cls.assert_called_once_with(mock_session)
            mock_event_service.run_lifecycle_transitions.assert_awaited_once_with(
                stale_hours=12,
                archive_hours=36,
            )

    asyncio.run(_test())


def test_run_lifecycle_propagates_transition_failures() -> None:
    async def _test() -> None:
        mock_event_service = AsyncMock()
        mock_event_service.run_lifecycle_transitions.side_effect = RuntimeError(
            "database unavailable"
        )

        with (
            patch(
                "hermes_worker.services.lifecycle.AsyncSessionLocal"
            ) as mock_session_cls,
            patch(
                "hermes_worker.services.lifecycle.EventService",
                return_value=mock_event_service,
            ),
        ):
            mock_session_cls.return_value.__aenter__.return_value = AsyncMock()

            with pytest.raises(RuntimeError, match="database unavailable"):
                await run_lifecycle(_settings())

    asyncio.run(_test())
