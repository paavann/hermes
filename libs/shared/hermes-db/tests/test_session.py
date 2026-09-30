"""Tests for hermes_db.session — get_db, init_db, close_db.

All tests fully mock the SQLAlchemy async engine so no real database is
required.  The engine-level module globals (``engine``,
``AsyncSessionLocal``) are patched via ``unittest.mock.patch``.
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from conftest import run


# ---------------------------------------------------------------------------
# get_db — async generator that yields a session
# ---------------------------------------------------------------------------


class TestGetDb:
    def test_yields_session_on_happy_path(self):
        """get_db must yield the session created by AsyncSessionLocal."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_session_factory = MagicMock(return_value=mock_session)

        with patch("hermes_db.session.AsyncSessionLocal", mock_session_factory):
            from hermes_db.session import get_db

            async def _consume():
                async for s in get_db():
                    return s

            result = run(_consume())
        assert result is mock_session

    def test_rolls_back_on_exception(self):
        """If the caller raises inside get_db, session.rollback must be called."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.rollback = AsyncMock()

        mock_session_factory = MagicMock(return_value=mock_session)

        with patch("hermes_db.session.AsyncSessionLocal", mock_session_factory):
            from hermes_db.session import get_db

            async def _raise():
                async for _s in get_db():
                    raise RuntimeError("simulated error")

            with pytest.raises(RuntimeError, match="simulated error"):
                run(_raise())

        mock_session.rollback.assert_awaited_once()

    def test_exception_is_re_raised(self):
        """After rollback, the original exception must propagate to the caller."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.rollback = AsyncMock()

        with patch("hermes_db.session.AsyncSessionLocal", MagicMock(return_value=mock_session)):
            from hermes_db.session import get_db

            class _CustomError(Exception):
                pass

            async def _raise():
                async for _s in get_db():
                    raise _CustomError("boom")

            with pytest.raises(_CustomError, match="boom"):
                run(_raise())


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------


class TestInitDb:
    def _make_engine_mock(self, *, conn_raises: Exception | None = None) -> MagicMock:
        """Build a fake engine with a controllable begin() context manager."""
        conn = AsyncMock()
        conn.execute = AsyncMock(side_effect=conn_raises)

        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=conn)
        cm.__aexit__ = AsyncMock(return_value=False)

        engine = MagicMock()
        engine.begin = MagicMock(return_value=cm)
        return engine

    def test_logs_success_on_connection(self, caplog):
        """A successful connection must emit an INFO log."""
        engine = self._make_engine_mock()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory = MagicMock(return_value=mock_session)

        with (
            patch("hermes_db.session.engine", engine),
            patch("hermes_db.session.AsyncSessionLocal", mock_factory),
            patch("hermes_db.session.sync_sources_from_config", new_callable=AsyncMock),
            caplog.at_level(logging.INFO, logger="hermes_db.session"),
        ):
            from hermes_db.session import init_db

            run(init_db())

        assert any("successfully connected" in r.message for r in caplog.records)

    def test_raises_and_logs_error_on_connection_failure(self, caplog):
        """A DB connection failure must re-raise and emit an ERROR log."""
        engine = self._make_engine_mock(conn_raises=OSError("refused"))

        with (
            patch("hermes_db.session.engine", engine),
            caplog.at_level(logging.ERROR, logger="hermes_db.session"),
        ):
            from hermes_db.session import init_db

            with pytest.raises(OSError, match="refused"):
                run(init_db())

        assert any("failed to connect" in r.message for r in caplog.records)

    def test_source_sync_called_on_success(self):
        """After connecting, sync_sources_from_config must be awaited."""
        engine = self._make_engine_mock()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory = MagicMock(return_value=mock_session)
        mock_sync = AsyncMock()

        with (
            patch("hermes_db.session.engine", engine),
            patch("hermes_db.session.AsyncSessionLocal", mock_factory),
            patch("hermes_db.session.sync_sources_from_config", mock_sync),
        ):
            from hermes_db.session import init_db

            run(init_db())

        mock_sync.assert_awaited_once()

    def test_sync_failure_does_not_propagate(self, caplog):
        """A sync_sources failure must be caught and logged, not raised."""
        engine = self._make_engine_mock()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory = MagicMock(return_value=mock_session)
        mock_sync = AsyncMock(side_effect=RuntimeError("sync boom"))

        with (
            patch("hermes_db.session.engine", engine),
            patch("hermes_db.session.AsyncSessionLocal", mock_factory),
            patch("hermes_db.session.sync_sources_from_config", mock_sync),
            caplog.at_level(logging.ERROR, logger="hermes_db.session"),
        ):
            from hermes_db.session import init_db

            # Must NOT raise — sync failure is swallowed.
            run(init_db())

        assert any("failed to sync" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# close_db
# ---------------------------------------------------------------------------


class TestCloseDb:
    def test_disposes_engine(self):
        """close_db must call engine.dispose() to release connection pool."""
        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("hermes_db.session.engine", mock_engine):
            from hermes_db.session import close_db

            run(close_db())

        mock_engine.dispose.assert_awaited_once()

    def test_logs_closure_message(self, caplog):
        """After disposing, an INFO log must be emitted."""
        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with (
            patch("hermes_db.session.engine", mock_engine),
            caplog.at_level(logging.INFO, logger="hermes_db.session"),
        ):
            from hermes_db.session import close_db

            run(close_db())

        assert any("closed" in r.message for r in caplog.records)
