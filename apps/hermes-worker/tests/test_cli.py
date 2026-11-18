"""Unit tests for the Hermes worker CLI, command handlers, and lifespan manager."""

import argparse
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from hermes_worker.cli import build_parser, main, run_app
from hermes_worker.core.lifespan import db_lifespan
from hermes_worker.handlers.commands import (
    WorkerCmd,
    handle_audit_sources,
    handle_healthcheck,
    handle_ingest_articles,
    handle_maintain_events,
    handle_reset_db,
)
from hermes_worker.services.reset import ResetGuardError


def test_build_parser_commands():
    """Verifies CLI argument parsing and handler dispatch bindings."""
    parser = build_parser()

    args_ingest = parser.parse_args(["ingest-articles"])
    assert args_ingest.command == WorkerCmd.INGEST_ARTICLES.value
    assert args_ingest.handler is handle_ingest_articles
    assert args_ingest.force is False

    args_force = parser.parse_args(["ingest-articles", "--force"])
    assert args_force.force is True

    args_maint = parser.parse_args(["maintain-events"])
    assert args_maint.command == WorkerCmd.MAINTAIN_EVENTS.value
    assert args_maint.handler is handle_maintain_events

    args_check = parser.parse_args(["healthcheck"])
    assert args_check.command == WorkerCmd.HEALTHCHECK.value
    assert args_check.handler is handle_healthcheck

    args_audit = parser.parse_args(["audit-sources"])
    assert args_audit.command == WorkerCmd.AUDIT_SOURCES.value
    assert args_audit.handler is handle_audit_sources
    assert args_audit.requires_db is False

    args_reset = parser.parse_args(["reset-db", "--yes"])
    assert args_reset.command == WorkerCmd.RESET.value
    assert args_reset.yes
    assert args_reset.requires_local_db is True
    assert args_reset.handler is handle_reset_db


@pytest.mark.parametrize(
    "command",
    ["run-sync", "run-all", "run-lifecycle", "pipeline-ingest"],
)
def test_legacy_commands_are_gone(command: str):
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([command])


def test_build_parser_reset_requires_confirmation():
    """reset-db must fail argument parsing without --yes."""
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["reset-db"])


def test_handle_ingest_articles_delegates():
    async def _test():
        with patch(
            "hermes_worker.handlers.commands.run_ingest_articles",
            new_callable=AsyncMock,
        ) as mock_run:
            await handle_ingest_articles(
                argparse.Namespace(force=True),
            )

        mock_run.assert_awaited_once()
        assert mock_run.await_args.kwargs["force"] is True

    asyncio.run(_test())


def test_handle_maintain_events_delegates():
    async def _test():
        with patch(
            "hermes_worker.handlers.commands.run_maintain_events",
            new_callable=AsyncMock,
        ) as mock_run:
            await handle_maintain_events(argparse.Namespace())

        mock_run.assert_awaited_once()

    asyncio.run(_test())


def test_handle_healthcheck_delegates():
    async def _test():
        with patch(
            "hermes_worker.handlers.commands.run_healthcheck",
            new_callable=AsyncMock,
        ) as mock_run:
            await handle_healthcheck(argparse.Namespace())

        mock_run.assert_awaited_once()

    asyncio.run(_test())


def test_handle_reset_db_requires_confirmation():
    """The handler must refuse to run without --yes even if called directly."""

    async def _test():
        with pytest.raises(ResetGuardError, match="--yes"):
            await handle_reset_db(argparse.Namespace())

    asyncio.run(_test())


def test_handle_reset_db_rejects_unsafe_target():
    """A guard failure must stop the reset before opening a session."""

    async def _test():
        with (
            patch(
                "hermes_worker.handlers.commands.validate_reset_target",
                side_effect=ResetGuardError("unsafe target"),
            ),
            patch("hermes_worker.handlers.commands.AsyncSessionLocal") as mock_factory,
        ):
            with pytest.raises(ResetGuardError, match="unsafe target"):
                await handle_reset_db(argparse.Namespace(yes=True))
            mock_factory.assert_not_called()

    asyncio.run(_test())


def test_handle_reset_db_runs_schema_reset():
    """A confirmed local target must reset through the initialized session."""

    async def _test():
        session = AsyncMock()
        session_cm = AsyncMock()
        session_cm.__aenter__ = AsyncMock(return_value=session)
        session_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "hermes_worker.handlers.commands.validate_reset_target"
            ) as mock_validate,
            patch(
                "hermes_worker.handlers.commands.AsyncSessionLocal",
                return_value=session_cm,
            ),
            patch(
                "hermes_worker.handlers.commands.reset_local_schema",
                new_callable=AsyncMock,
            ) as mock_reset,
        ):
            await handle_reset_db(argparse.Namespace(yes=True))

        mock_validate.assert_called_once()
        mock_reset.assert_awaited_once_with(session)

    asyncio.run(_test())


def test_handle_audit_sources_prints_report():
    async def _test():
        audit = object()
        with (
            patch(
                "hermes_worker.handlers.commands.load_sources_config",
                new_callable=AsyncMock,
                return_value=[{"slug": "bbc-world"}],
            ),
            patch(
                "hermes_worker.handlers.commands.audit_sources",
                new_callable=AsyncMock,
                return_value=[audit],
            ) as mock_audit,
            patch(
                "hermes_worker.handlers.commands.format_audit",
                return_value=["bbc-world | report line"],
            ) as mock_format,
        ):
            await handle_audit_sources(argparse.Namespace())

        mock_audit.assert_awaited_once()
        mock_format.assert_called_once_with([audit])

    asyncio.run(_test())


def test_run_app_skips_db_for_audit():
    """audit-sources is a network probe and must not open a database session."""

    async def _test():
        mock_handler = AsyncMock()
        args = argparse.Namespace(
            command="audit-sources",
            handler=mock_handler,
            requires_db=False,
        )

        with patch("hermes_worker.cli.db_lifespan") as mock_lifespan:
            code = await run_app(args)

        assert code == 0
        mock_lifespan.assert_not_called()
        mock_handler.assert_awaited_once_with(args)

    asyncio.run(_test())


def test_run_app_blocks_unsafe_reset_before_lifespan():
    """The reset guard must run before the database engine is initialized."""

    async def _test():
        mock_handler = AsyncMock()
        args = argparse.Namespace(
            command="reset-db",
            handler=mock_handler,
            requires_local_db=True,
        )

        with (
            patch(
                "hermes_worker.cli.validate_reset_target",
                side_effect=ResetGuardError("unsafe target"),
            ) as mock_guard,
            patch("hermes_worker.cli.db_lifespan") as mock_lifespan,
        ):
            code = await run_app(args)

        assert code == 1
        mock_guard.assert_called_once()
        mock_lifespan.assert_not_called()
        mock_handler.assert_not_awaited()

    asyncio.run(_test())


def test_db_lifespan():
    """Verifies that the db_lifespan context manager initializes and closes connections."""

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
        args = argparse.Namespace(command="maintain-events", handler=mock_handler)

        with patch("hermes_worker.cli.db_lifespan") as mock_lifespan:
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
        args = argparse.Namespace(command="maintain-events", handler=mock_handler)

        with patch("hermes_worker.cli.db_lifespan") as mock_lifespan:
            mock_cm = AsyncMock()
            mock_lifespan.return_value = mock_cm

            code = await run_app(args)
            assert code == 1

    asyncio.run(_test())


def test_run_app_maintain_events():
    """Verifies that run_app coordinates database lifespan and maintenance."""

    async def _test():
        parser = build_parser()
        args = parser.parse_args(["maintain-events"])

        with (
            patch("hermes_worker.core.lifespan.init_db", new_callable=AsyncMock),
            patch("hermes_worker.core.lifespan.close_db", new_callable=AsyncMock),
            patch(
                "hermes_worker.handlers.commands.run_maintain_events",
                new_callable=AsyncMock,
            ) as mock_maint,
        ):
            code = await run_app(args)
            assert code == 0
            mock_maint.assert_awaited_once()

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
