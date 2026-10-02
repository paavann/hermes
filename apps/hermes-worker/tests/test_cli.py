import asyncio
from unittest.mock import AsyncMock, patch
from hermes_worker.cli import _run_command, build_parser


def test_build_parser_commands():
    parser = build_parser()

    # run-sync
    args = parser.parse_args(["run-sync"])
    assert args.command == "run-sync"
    assert not args.force

    args_force = parser.parse_args(["run-sync", "--force"])
    assert args_force.command == "run-sync"
    assert args_force.force

    # run-lifecycle
    args_life = parser.parse_args(["run-lifecycle"])
    assert args_life.command == "run-lifecycle"

    # run-all
    args_all = parser.parse_args(["run-all", "--force"])
    assert args_all.command == "run-all"
    assert args_all.force


def test_run_command_lifecycle():
    async def _test():
        with (
            patch("hermes_worker.cli.init_db", new_callable=AsyncMock) as mock_init,
            patch("hermes_worker.cli.close_db", new_callable=AsyncMock) as mock_close,
            patch(
                "hermes_worker.cli.run_lifecycle", new_callable=AsyncMock
            ) as mock_run_life,
        ):
            mock_run_life.return_value = {"decayed": 5}
            code = await _run_command("run-lifecycle")

            assert code == 0
            mock_init.assert_awaited_once()
            mock_run_life.assert_awaited_once()
            mock_close.assert_awaited_once()

    asyncio.run(_test())


def test_run_command_sync():
    async def _test():
        with (
            patch("hermes_worker.cli.init_db", new_callable=AsyncMock) as mock_init,
            patch("hermes_worker.cli.close_db", new_callable=AsyncMock) as mock_close,
            patch("hermes_worker.cli.SyncService") as mock_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.sync_all_sources = AsyncMock(
                return_value={"events_created": 2}
            )

            code = await _run_command("run-sync", force=True)

            assert code == 0
            mock_init.assert_awaited_once()
            mock_service.sync_all_sources.assert_awaited_once_with(force=True)
            mock_close.assert_awaited_once()

    asyncio.run(_test())
