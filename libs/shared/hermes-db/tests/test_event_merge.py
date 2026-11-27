"""Tests for event merging and merge idempotency."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from conftest import make_async_session, make_uuid, run

from hermes_db.enums import EventRelationshipType, EventScope, EventStatus
from hermes_db.models.event import Event
from hermes_db.models.event_relationship import EventRelationship
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
        assert session.execute.await_count == 5
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

    def test_repoints_unique_edges_and_deletes_conflicting_edges(self):
        survivor = _event(event_id=make_uuid())
        loser = _event(event_id=make_uuid())
        third_unique = make_uuid()
        third_shared = make_uuid()

        survivor_to_shared = EventRelationship(
            id=make_uuid(),
            source_event_id=survivor.id,
            target_event_id=third_shared,
            relationship_type=EventRelationshipType.RELATED,
            confidence=0.9,
            rationale="Existing link",
            pair_hash="h1",
        )
        loser_to_unique = EventRelationship(
            id=make_uuid(),
            source_event_id=loser.id,
            target_event_id=third_unique,
            relationship_type=EventRelationshipType.REACTION,
            confidence=0.85,
            rationale="Watch party",
            pair_hash="h2",
        )
        loser_to_shared = EventRelationship(
            id=make_uuid(),
            source_event_id=third_shared,
            target_event_id=loser.id,
            relationship_type=EventRelationshipType.CAUSED,
            confidence=0.75,
            rationale="Duplicate third-party link",
            pair_hash="h3",
        )

        empty_result = MagicMock()
        select_result = MagicMock()
        select_scalars = MagicMock()
        select_scalars.all.return_value = [
            survivor_to_shared,
            loser_to_unique,
            loser_to_shared,
        ]
        select_result.scalars.return_value = select_scalars

        session = make_async_session()
        session.scalar = AsyncMock(return_value=None)
        session.get = AsyncMock(side_effect=[loser, survivor])
        session.execute = AsyncMock(
            side_effect=[
                empty_result,
                empty_result,
                empty_result,
                empty_result,
                select_result,
                empty_result,
            ]
        )

        aggregate = MagicMock()
        aggregate.latest_published_at = NOW
        with patch(
            "hermes_db.services.event_merge.EventMembershipService"
        ) as membership_cls:
            membership_cls.return_value.recompute = AsyncMock(return_value=aggregate)
            merged = run(
                EventMergeService(session).merge(
                    survivor_id=survivor.id,
                    loser_id=loser.id,
                    reason="dup",
                    now=NOW,
                )
            )

        assert merged is True
        assert loser_to_unique.source_event_id == survivor.id
        assert session.execute.await_count == 6
        delete_stmt = session.execute.call_args_list[-1].args[0]
        assert loser_to_shared.id in delete_stmt.compile().params["id_1"]


class TestRecentStates:
    def test_hydrates_actors_on_event_pair_state(self):
        event_id = make_uuid()
        row = MagicMock()
        row.id = event_id
        row.ai_headline = "Israeli attacks on Gaza"
        row.ai_summary = "Summary"
        row.category = "CONFLICT"
        row.event_time = NOW
        row.latest_published_at = NOW
        row.first_reported_at = NOW
        row.country_code = "PS"
        row.location_name = "Gaza Strip"
        row.latitude = 31.54
        row.longitude = 34.46
        row.embedding = [0.1, 0.2]
        row.embedding_model = "embed-1"
        row.member_hash = "mh"
        row.article_count = 1
        row.thread_id = None
        row.status = EventStatus.ACTIVE
        row.scope = EventScope.CITY
        row.actors = [{"name": "Israel", "kind": "STATE", "role": "ACTOR", "country_code": "IL"}]

        session = make_async_session(execute_all=[row])
        states = run(EventMergeService(session).recent_states(since=NOW, limit=10))

        assert len(states) == 1
        assert states[0].actors == (
            {"name": "Israel", "kind": "STATE", "role": "ACTOR", "country_code": "IL"},
        )
