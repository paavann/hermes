import asyncio
from unittest.mock import AsyncMock, patch
from hermes_worker.services.lifecycle import run_lifecycle


def test_run_lifecycle_executes_transitions():
    async def _test():
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
            ),
        ):
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            stats = await run_lifecycle()

            assert stats["decayed_events"] == 10
            mock_event_service.run_lifecycle_transitions.assert_awaited_once()

    asyncio.run(_test())
