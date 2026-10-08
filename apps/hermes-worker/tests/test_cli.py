"""Unit tests for the Hermes worker CLI, command handlers, and lifespan manager."""

import argparse
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from hermes_worker.cli import _run_command, build_parser, main, run_app
from hermes_worker.core.lifespan import db_lifespan
from hermes_worker.handlers.commands import (
    WorkerCmd,
    handle_all,
    handle_lifecycle,
    handle_sync,
)


def test_build_parser_commands():
    """Verifies CLI argument parsing and handler dispatch bindings."""
    parser = build_parser()

    # run-sync.
    args = parser.parse_args(["run-sync"])
    assert args.command == WorkerCmd.SYNC.value
    assert not args.force
    assert args.handler is handle_sync

    args_force = parser.parse_args(["run-sync", "--force"])
    assert args_force.command == WorkerCmd.SYNC.value
    assert args_force.force
    assert args_force.handler is handle_sync

    # run-lifecycle.
    args_life = parser.parse_args(["run-lifecycle"])
    assert args_life.command == WorkerCmd.LIFECYCLE.value
    assert args_life.handler is handle_lifecycle

    # run-all.
    args_all = parser.parse_args(["run-all", "--force"])
    assert args_all.command == WorkerCmd.ALL.value
    assert args_all.force
    assert args_all.handler is handle_all


def test_handle_sync():
    """Verifies that handle_sync invokes the sync service with arguments."""

    async def _test():
        with patch("hermes_worker.handlers.commands.SyncService") as mock_cls:
            mock_service = mock_cls.return_value
            mock_service.sync_all_sources = AsyncMock(return_value={"created": 1})

            args = argparse.Namespace(force=True)
            await handle_sync(args)

            mock_service.sync_all_sources.assert_awaited_once_with(force=True)

    asyncio.run(_test())


def test_handle_lifecycle():
    """Verifies that handle_lifecycle invokes run_lifecycle."""

    async def _test():
        with patch(
            "hermes_worker.handlers.commands.run_lifecycle", new_callable=AsyncMock
        ) as mock_life:
            mock_life.return_value = {"decayed": 3}

            args = argparse.Namespace()
            await handle_lifecycle(args)

            mock_life.assert_awaited_once()

    asyncio.run(_test())


def test_handle_all():
    """Verifies that handle_all coordinates lifecycle transitions and source sync."""

    async def _test():
        with (
            patch(
                "hermes_worker.handlers.commands.run_lifecycle",
                new_callable=AsyncMock,
            ) as mock_life,
            patch("hermes_worker.handlers.commands.SyncService") as mock_cls,
        ):
            mock_life.return_value = {"decayed": 2}
            mock_service = mock_cls.return_value
            mock_service.sync_all_sources = AsyncMock(return_value={"created": 4})

            args = argparse.Namespace(force=True)
            await handle_all(args)

            mock_life.assert_awaited_once()
            mock_service.sync_all_sources.assert_awaited_once_with(force=True)

    asyncio.run(_test())


def test_db_lifespan():
    """Verifies that the db_lifespan context manager correctly initializes and closes connections."""

    async def _test():
        with (
            patch(
                "hermes_worker.core.lifespan.init_db", new_callable=AsyncMock
            ) as mock_init,
            patch(
                "hermes_worker.core.lifespan.close_db", new_callable=AsyncMock
            ) as mock_close,
        ):
            async with db_lifespan():
                mock_init.assert_awaited_once()
                mock_close.assert_not_awaited()

            mock_close.assert_awaited_once()

    asyncio.run(_test())


def test_run_app_success():
    """Verifies successful execution flow of run_app."""

    async def _test():
        mock_handler = AsyncMock()
        args = argparse.Namespace(command="run-sync", handler=mock_handler)

        with patch("hermes_worker.cli.db_lifespan") as mock_lifespan:
            # Mock the async context manager protocol
            mock_cm = AsyncMock()
            mock_lifespan.return_value = mock_cm

            code = await run_app(args)
            assert code == 0
            mock_handler.assert_awaited_once_with(args)

    asyncio.run(_test())


def test_run_app_missing_handler():
    """Verifies that run_app returns 1 when no handler is attached."""

    async def _test():
        args = argparse.Namespace(command="unknown")
        code = await run_app(args)
        assert code == 1

    asyncio.run(_test())


def test_run_app_exception():
    """Verifies that run_app logs exceptions and returns 1 on failure."""

    async def _test():
        mock_handler = AsyncMock(side_effect=RuntimeError("connection error"))
        args = argparse.Namespace(command="run-sync", handler=mock_handler)

        with patch("hermes_worker.cli.db_lifespan") as mock_lifespan:
            mock_cm = AsyncMock()
            mock_lifespan.return_value = mock_cm

            code = await run_app(args)
            assert code == 1

    asyncio.run(_test())


def test_run_command_compat():
    """Verifies backward compatibility of the _run_command helper function."""

    async def _test():
        with (
            patch("hermes_worker.core.lifespan.init_db", new_callable=AsyncMock),
            patch("hermes_worker.core.lifespan.close_db", new_callable=AsyncMock),
            patch(
                "hermes_worker.handlers.commands.run_lifecycle",
                new_callable=AsyncMock,
            ) as mock_life,
        ):
            mock_life.return_value = {"decayed": 1}
            code = await _run_command("run-lifecycle")
            assert code == 0

        # Invalid command string should return 1.
        bad_code = await _run_command("non-existent-command")
        assert bad_code == 1

    asyncio.run(_test())


def test_main():
    """Verifies the main entry point function parses arguments and runs."""
    with (
        patch("hermes_worker.cli.setup_logging") as mock_setup,
        patch("hermes_worker.cli.build_parser") as mock_parser_builder,
        patch("hermes_worker.cli.run_app", new_callable=AsyncMock) as mock_run_app,
        patch("sys.exit") as mock_exit,
    ):
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_parser.parse_args.return_value = mock_args
        mock_parser_builder.return_value = mock_parser
        mock_run_app.return_value = 0

        main()

        mock_setup.assert_called_once()
        mock_parser.parse_args.assert_called_once()
        mock_run_app.assert_awaited_once_with(mock_args)
        mock_exit.assert_called_once_with(0)
