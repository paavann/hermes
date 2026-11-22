"""Tests for hermes_db.services.thread — ThreadService.

All tests use a mocked AsyncSession so no database is involved.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from conftest import make_async_session, make_uuid, run
from sqlalchemy.engine import CursorResult

from hermes_db.enums import ThreadKind, ThreadStatus
from hermes_db.models.thread import Thread
from hermes_db.services.thread import (
    ThreadEventSnapshot,
    ThreadService,
    normalize_name,
)


NOW = datetime(2026, 11, 20, 12, 0, 0, tzinfo=UTC)


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

        event_stmt = session.execute.call_args_list[0].args[0]
        params = event_stmt.compile().params
        assert params["id_1"] == event_id
        assert params["thread_id"] == thread_id

    def test_returns_false_when_event_missing(self):
        session = make_async_session()
        result = MagicMock(spec=CursorResult)
        result.rowcount = 0
        session.execute.return_value = result
        svc = ThreadService(session)

        assert run(svc.assign_event(make_uuid(), make_uuid())) is False


def _snapshot(
    *,
    embedding: tuple[float, ...] | None = None,
    entities: frozenset[str] = frozenset(),
    embedding_model: str | None = "test-embed",
) -> ThreadEventSnapshot:
    return ThreadEventSnapshot(
        id=make_uuid(),
        ai_headline="Explosion hits market",
        ai_summary="An explosion struck the central market.",
        category="CONFLICT",
        event_time=NOW,
        latest_published_at=NOW,
        first_reported_at=NOW,
        importance_score=70.0,
        latitude=50.45,
        longitude=30.52,
        embedding=embedding,
        embedding_model=embedding_model,
        facts=("An explosion struck the central market.",),
        entities=entities,
        locations=("Kyiv",),
    )


def _candidate_row(
    *,
    thread_id: object,
    embedding: tuple[float, ...] | None,
    entities: list[dict[str, object]],
    last_event_at: datetime | None = NOW,
    embedding_model: str | None = "test-embed",
) -> MagicMock:
    row = MagicMock()
    row.id = thread_id
    row.name = "Kyiv strikes"
    row.description = "Tracking strikes on Kyiv."
    row.kind = ThreadKind.DEVELOPING
    row.status = ThreadStatus.ACTIVE
    row.last_event_at = last_event_at
    row.importance = 60.0
    row.event_count = 3
    row.embedding = embedding
    row.embedding_model = embedding_model
    row.entities = entities
    return row


class TestNormalizeName:
    def test_casefolds_and_collapses_whitespace(self):
        assert normalize_name("  Red   Sea\nShipping ") == "red sea shipping"

    def test_truncates_to_255_characters(self):
        assert len(normalize_name("x" * 400)) == 255


class TestRankedCandidates:
    def test_ranks_embedding_and_entity_overlap(self):
        thread_id = make_uuid()
        session = make_async_session(
            execute_all=[
                _candidate_row(
                    thread_id=thread_id,
                    embedding=(1.0, 0.0, 0.0, 0.0),
                    entities=[{"name": "Kyiv"}],
                )
            ]
        )
        svc = ThreadService(session)

        matches = run(
            svc.ranked_candidates(
                _snapshot(
                    embedding=(1.0, 0.0, 0.0, 0.0),
                    entities=frozenset({"kyiv"}),
                )
            )
        )

        assert len(matches) == 1
        match = matches[0]
        assert match.candidate.id == thread_id
        assert match.embedding_similarity == 1.0
        assert match.entity_similarity == 1.0
        assert match.score == 1.0

    def test_skips_embedding_from_other_model(self):
        session = make_async_session(
            execute_all=[
                _candidate_row(
                    thread_id=make_uuid(),
                    embedding=(1.0, 0.0),
                    entities=[{"name": "Kyiv"}],
                    embedding_model="other-model",
                )
            ]
        )
        svc = ThreadService(session)

        matches = run(
            svc.ranked_candidates(
                _snapshot(
                    embedding=(1.0, 0.0),
                    entities=frozenset({"kyiv"}),
                )
            )
        )

        assert matches[0].embedding_similarity == 0.0
        assert matches[0].score == 0.3

    def test_skips_embedding_with_different_dimensions(self):
        session = make_async_session(
            execute_all=[
                _candidate_row(
                    thread_id=make_uuid(),
                    embedding=(1.0, 0.0, 0.0),
                    entities=[],
                )
            ]
        )
        svc = ThreadService(session)

        matches = run(
            svc.ranked_candidates(_snapshot(embedding=(1.0, 0.0)))
        )

        assert matches[0].embedding_similarity == 0.0
        assert matches[0].entity_similarity == 0.0

    def test_sorts_highest_score_first(self):
        low_id = make_uuid()
        high_id = make_uuid()
        session = make_async_session(
            execute_all=[
                _candidate_row(
                    thread_id=low_id,
                    embedding=(0.0, 1.0),
                    entities=[],
                ),
                _candidate_row(
                    thread_id=high_id,
                    embedding=(1.0, 0.0),
                    entities=[{"name": "Kyiv"}],
                ),
            ]
        )
        svc = ThreadService(session)

        matches = run(
            svc.ranked_candidates(
                _snapshot(
                    embedding=(1.0, 0.0),
                    entities=frozenset({"kyiv"}),
                )
            )
        )

        assert [match.candidate.id for match in matches] == [high_id, low_id]


class TestRecompute:
    def test_updates_counts_entities_keywords_and_centroid(self):
        thread = MagicMock(spec=Thread)
        thread.name = "Kyiv strikes"
        thread.id = make_uuid()

        row = MagicMock()
        row.id = make_uuid()
        row.importance_score = 80.0
        row.event_time = NOW
        row.latest_published_at = NOW
        row.first_reported_at = NOW
        row.embedding = (1.0, 0.0)

        session = make_async_session(get_return=thread, execute_all=[row])

        member = MagicMock()
        member.event_id = row.id
        member.entities = ({"name": "Kyiv", "kind": "LOCATION"},)
        member.fact = "Explosion reported in the capital."

        svc = ThreadService(session)
        svc._membership.current_members = AsyncMock(return_value=[member])

        result = run(svc.recompute(thread.id, now=NOW))

        assert result is thread
        assert thread.event_count == 1
        assert thread.last_event_at == NOW
        assert thread.importance == 80.0
        assert thread.embedding == [1.0, 0.0]
        assert thread.entities == [{"name": "Kyiv", "kind": "LOCATION"}]
        assert "explosion" in thread.keywords
        assert thread.name_norm == "kyiv strikes"

    def test_returns_none_for_missing_thread(self):
        session = make_async_session(get_return=None)
        svc = ThreadService(session)

        assert run(svc.recompute(make_uuid(), now=NOW)) is None


class TestRunLifecycle:
    def test_reports_dormant_and_ended_counts(self):
        session = make_async_session()
        dormant_result = MagicMock(spec=CursorResult)
        dormant_result.rowcount = 4
        ended_result = MagicMock(spec=CursorResult)
        ended_result.rowcount = 2
        session.execute = AsyncMock(side_effect=[dormant_result, ended_result])
        svc = ThreadService(session)

        counts = run(svc.run_lifecycle(now=NOW))

        assert counts == {"dormant": 4, "ended": 2}
        assert session.execute.await_count == 2

    def test_uses_configured_cutoffs(self):
        session = make_async_session()
        result = MagicMock(spec=CursorResult)
        result.rowcount = 0
        session.execute = AsyncMock(return_value=result)
        svc = ThreadService(session)

        counts = run(svc.run_lifecycle(now=NOW, dormant_days=3, ended_days=10))

        assert counts == {"dormant": 0, "ended": 0}
        first_stmt = session.execute.call_args_list[0].args[0]
        params = first_stmt.compile().params
        cutoff = next(
            value for key, value in params.items() if key.startswith("last_event_at")
        )
        assert cutoff == NOW - timedelta(days=3)


class TestCount:
    def test_counts_all_threads(self):
        session = make_async_session()
        session.scalar = AsyncMock(return_value=7)
        svc = ThreadService(session)

        assert run(svc.count()) == 7

    def test_counts_by_status(self):
        session = make_async_session()
        session.scalar = AsyncMock(return_value=3)
        svc = ThreadService(session)

        assert run(svc.count(ThreadStatus.DORMANT)) == 3
