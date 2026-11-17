"""Tests for hermes_db.services.thread — ThreadService.

All tests use a mocked AsyncSession so no database is involved.
"""

from unittest.mock import MagicMock

from conftest import make_async_session, make_uuid, run
from sqlalchemy.engine import CursorResult

from hermes_db.enums import ThreadKind, ThreadStatus
from hermes_db.models.thread import Thread
from hermes_db.services.thread import ThreadService


class TestCreateThread:
    def test_adds_and_flushes_thread(self):
        session = make_async_session()
        svc = ThreadService(session)

        thread = run(svc.create_thread("Red Sea shipping disruptions"))

        session.add.assert_called_once_with(thread)
        session.flush.assert_awaited_once()
        assert isinstance(thread, Thread)
        assert thread.kind == ThreadKind.DEVELOPING
        assert Thread.status.default.arg == ThreadStatus.ACTIVE
        assert thread.entities == []
        assert thread.keywords == []

    def test_passes_optional_fields(self):
        session = make_async_session()
        svc = ThreadService(session)

        thread = run(
            svc.create_thread(
                "Election monitoring",
                kind=ThreadKind.TOPIC,
                description="Tracking vote-count disputes.",
                entities=[{"name": "Election Commission", "type": "org"}],
                keywords=["election", "recount"],
            )
        )

        assert thread.kind == ThreadKind.TOPIC
        assert thread.description == "Tracking vote-count disputes."
        assert thread.entities == [{"name": "Election Commission", "type": "org"}]
        assert thread.keywords == ["election", "recount"]


class TestGetThread:
    def test_uses_session_get(self):
        stored = MagicMock(spec=Thread)
        session = make_async_session(get_return=stored)
        svc = ThreadService(session)
        thread_id = make_uuid()

        assert run(svc.get_thread(thread_id)) is stored
        session.get.assert_awaited_once_with(Thread, thread_id)


class TestAssignEvent:
    def test_returns_true_when_event_updated(self):
        session = make_async_session()
        result = MagicMock(spec=CursorResult)
        result.rowcount = 1
        session.execute.return_value = result
        svc = ThreadService(session)
        event_id = make_uuid()
        thread_id = make_uuid()

        assert run(svc.assign_event(event_id, thread_id)) is True

        stmt = session.execute.call_args.args[0]
        params = stmt.compile().params
        assert params["id_1"] == event_id
        assert params["thread_id"] == thread_id

    def test_returns_false_when_event_missing(self):
        session = make_async_session()
        result = MagicMock(spec=CursorResult)
        result.rowcount = 0
        session.execute.return_value = result
        svc = ThreadService(session)

        assert run(svc.assign_event(make_uuid(), make_uuid())) is False
