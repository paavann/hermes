"""Tests for event merging and merge idempotency."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from conftest import make_async_session, make_uuid, run

from hermes_db.enums import EventStatus
from hermes_db.models.event import Event
from hermes_db.services.event_merge import EventMergeService


NOW = datetime(2026, 11, 20, 12, 0, 0, tzinfo=UTC)


def _event(
    *,
    event_id: uuid.UUID,
    status: EventStatus = EventStatus.ACTIVE,
    merged_into_id: uuid.UUID | None = None,
    thread_id: uuid.UUID | None = None,
) -> MagicMock:
    event = MagicMock(spec=Event)
    event.id = event_id
    event.status = status
    event.merged_into_id = merged_into_id
    event.thread_id = thread_id
    event.member_hash = "old-hash"
    event.version = 3
    event.article_count = 2
    event.last_updated_at = NOW
    event.merged_at = None
    event.merge_reason = None
    return event


class TestResolveEventId:
    def test_returns_same_id_when_not_merged(self):
        session = make_async_session()
        session.scalar = AsyncMock(return_value=None)
        service = EventMergeService(session)
        event_id = make_uuid()

        assert run(service.resolve_event_id(event_id)) == event_id
        session.scalar.assert_awaited_once()

    def test_follows_merge_redirect_chain(self):
        first_id = make_uuid()
        second_id = make_uuid()
        session = make_async_session()
        session.scalar = AsyncMock(side_effect=[second_id, None])
        service = EventMergeService(session)

        assert run(service.resolve_event_id(first_id)) == second_id

    def test_breaks_merge_cycles(self):
        first_id = make_uuid()
        second_id = make_uuid()
        session = make_async_session()
        session.scalar = AsyncMock(side_effect=[second_id, first_id])
        service = EventMergeService(session)

        assert run(service.resolve_event_id(first_id)) == first_id


class TestMerge:
    def test_rejects_self_merge(self):
        session = make_async_session()
        service = EventMergeService(session)
        event_id = make_uuid()

        assert run(service.merge(survivor_id=event_id, loser_id=event_id, reason="dup")) is False
        session.get.assert_not_awaited()

    def test_returns_false_when_events_missing(self):
        session = make_async_session()
        session.scalar = AsyncMock(return_value=None)
        session.get = AsyncMock(return_value=None)
        service = EventMergeService(session)

        assert (
            run(
                service.merge(
                    survivor_id=make_uuid(),
                    loser_id=make_uuid(),
                    reason="dup",
                )
            )
            is False
        )

    def test_returns_false_when_already_merged(self):
        survivor_id = make_uuid()
        loser_id = make_uuid()
        loser = _event(event_id=loser_id, merged_into_id=survivor_id)
        survivor = _event(event_id=survivor_id)

        session = make_async_session()
        session.scalar = AsyncMock(return_value=None)
        session.get = AsyncMock(side_effect=[loser, survivor])
        service = EventMergeService(session)

        assert (
            run(
                service.merge(
                    survivor_id=survivor_id,
                    loser_id=loser_id,
                    reason="dup",
                )
            )
            is False
        )
        session.execute.assert_not_awaited()
        session.flush.assert_not_awaited()

    def test_returns_false_when_loser_is_merged_status(self):
        loser = _event(event_id=make_uuid(), status=EventStatus.MERGED)
        survivor = _event(event_id=make_uuid())

        session = make_async_session()
        session.scalar = AsyncMock(return_value=None)
        session.get = AsyncMock(side_effect=[loser, survivor])
        service = EventMergeService(session)

        assert (
            run(
                service.merge(
                    survivor_id=survivor.id,
                    loser_id=loser.id,
                    reason="dup",
                )
            )
            is False
        )

    def test_merge_moves_members_and_redirects_loser(self):
        thread_id = make_uuid()
        loser = _event(event_id=make_uuid(), thread_id=thread_id)
        survivor = _event(event_id=make_uuid())

        session = make_async_session()
        session.scalar = AsyncMock(return_value=None)
        session.get = AsyncMock(side_effect=[loser, survivor])

        aggregate = MagicMock()
        aggregate.latest_published_at = NOW

        with patch(
            "hermes_db.services.event_merge.EventMembershipService"
        ) as membership_cls:
            membership = membership_cls.return_value
            membership.recompute = AsyncMock(return_value=aggregate)
            service = EventMergeService(session)

            merged = run(
                service.merge(
                    survivor_id=survivor.id,
                    loser_id=loser.id,
                    reason="same incident",
                    now=NOW,
                )
            )

        assert merged is True
        assert session.execute.await_count == 3
        assert membership.recompute.await_args_list[0].args == (loser.id,)
        assert membership.recompute.await_args_list[1].args == (survivor.id,)
        session.flush.assert_awaited_once()

        assert loser.status == EventStatus.MERGED
        assert loser.merged_into_id == survivor.id
        assert loser.merged_at == NOW
        assert loser.merge_reason == "same incident"
        assert loser.thread_id is None
        assert loser.version == 4

        assert survivor.thread_id == thread_id
        assert survivor.member_hash is None
        assert survivor.latest_published_at == NOW
        assert survivor.version == 4
        assert survivor.last_updated_at == NOW

    def test_repeated_merge_is_idempotent(self):
        survivor_id = make_uuid()
        loser_id = make_uuid()
        loser = _event(event_id=loser_id)
        survivor = _event(event_id=survivor_id)

        session = make_async_session()
        session.scalar = AsyncMock(return_value=None)
        session.get = AsyncMock(side_effect=[loser, survivor, loser, survivor])

        aggregate = MagicMock()
        aggregate.latest_published_at = NOW

        with patch(
            "hermes_db.services.event_merge.EventMembershipService"
        ) as membership_cls:
            membership_cls.return_value.recompute = AsyncMock(return_value=aggregate)
            service = EventMergeService(session)

            assert (
                run(
                    service.merge(
                        survivor_id=survivor_id,
                        loser_id=loser_id,
                        reason="dup",
                        now=NOW,
                    )
                )
                is True
            )
            assert (
                run(
                    service.merge(
                        survivor_id=survivor_id,
                        loser_id=loser_id,
                        reason="dup",
                        now=NOW,
                    )
                )
                is False
            )

        assert loser.merged_into_id == survivor_id
