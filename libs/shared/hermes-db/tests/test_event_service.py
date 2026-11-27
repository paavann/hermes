"""Read-side tests for :class:`hermes_db.services.event.EventService`."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from conftest import make_async_session, make_uuid, run

from hermes_db.enums import EventScope, EventStatus
from hermes_db.models.event import Event
from hermes_db.services.event import EventService


def _result(
    *,
    scalars: list[object] | None = None,
    rows: list[object] | None = None,
    scalar_one_or_none: object | None = None,
):
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=scalars or [])
    result.scalars = MagicMock(return_value=scalars_mock)
    result.all = MagicMock(return_value=rows or [])
    result.scalar_one_or_none = MagicMock(return_value=scalar_one_or_none)
    return result


def test_get_events_returns_scalars() -> None:
    event = MagicMock(spec=Event)
    session = make_async_session(execute_scalars=[event])
    service = EventService(session)

    events = run(service.get_events(status=EventStatus.ACTIVE, limit=10))

    assert events == [event]
    session.execute.assert_awaited_once()
    session.commit.assert_not_awaited()


def test_get_events_accepts_scope_and_no_status() -> None:
    session = make_async_session(execute_scalars=[])
    service = EventService(session)

    assert run(service.get_events(status=None, scope=EventScope.CITY)) == []


def test_get_events_by_bbox_returns_rows() -> None:
    event = MagicMock(spec=Event)
    row = (event, -0.1, 51.5, "London")
    session = make_async_session(execute_all=[row])
    service = EventService(session)

    rows = run(
        service.get_events_by_bbox(
            north=52.0,
            south=51.0,
            east=1.0,
            west=-1.0,
        )
    )

    assert rows == [row]
    session.commit.assert_not_awaited()


def test_get_event_by_id_returns_survivor_after_merge_redirect() -> None:
    survivor_id = make_uuid()
    loser = MagicMock(spec=Event)
    loser.merged_into_id = survivor_id
    survivor = MagicMock(spec=Event)
    survivor.merged_into_id = None

    session = make_async_session()
    session.execute = AsyncMock(
        side_effect=[
            _result(scalar_one_or_none=loser),
            _result(scalar_one_or_none=survivor),
        ]
    )
    service = EventService(session)

    result = run(service.get_event_by_id(make_uuid()))

    assert result is survivor
    assert session.execute.await_count == 2


def test_get_event_by_id_returns_none_when_missing() -> None:
    session = make_async_session()
    session.execute = AsyncMock(return_value=_result(scalar_one_or_none=None))
    service = EventService(session)

    assert run(service.get_event_by_id(make_uuid())) is None


def test_get_event_by_id_breaks_merge_cycles() -> None:
    first_id = make_uuid()
    second_id = make_uuid()
    first = MagicMock(spec=Event)
    first.merged_into_id = second_id
    second = MagicMock(spec=Event)
    second.merged_into_id = first_id

    session = make_async_session()
    session.execute = AsyncMock(
        side_effect=[
            _result(scalar_one_or_none=first),
            _result(scalar_one_or_none=second),
        ]
    )
    service = EventService(session)

    assert run(service.get_event_by_id(first_id)) is None
    assert session.execute.await_count == 2


def test_get_active_events_maps_rows_to_dicts() -> None:
    event_id = uuid.uuid4()
    session = make_async_session(
        execute_all=[(event_id, "Headline", "Berlin", "POLITICS")]
    )
    service = EventService(session)

    result = run(service.get_active_events())

    assert result == [
        {
            "id": str(event_id),
            "headline": "Headline",
            "location_name": "Berlin",
            "category": "POLITICS",
        }
    ]


def test_get_active_events_normalizes_missing_location() -> None:
    session = make_async_session(
        execute_all=[(make_uuid(), "Headline", None, "POLITICS")]
    )
    service = EventService(session)

    assert run(service.get_active_events())[0]["location_name"] == "N/A"


def test_get_active_events_by_embeddings_deduplicates_and_skips_empty() -> None:
    event_id = uuid.uuid4()
    session = make_async_session(
        execute_all=[(event_id, "Headline", "City", "POLITICS")]
    )
    service = EventService(session)

    result = run(
        service.get_active_events_by_embeddings(
            [None, [], [0.1] * 8, [0.2] * 8]
        )
    )

    assert result == [
        {
            "id": str(event_id),
            "headline": "Headline",
            "location_name": "City",
            "category": "POLITICS",
        }
    ]
    assert session.execute.await_count == 2


def test_get_active_events_by_embeddings_empty_input_skips_query() -> None:
    session = make_async_session()
    service = EventService(session)

    assert run(service.get_active_events_by_embeddings([])) == []
    session.execute.assert_not_awaited()


def test_event_timestamp_defaults_are_utc() -> None:
    event = MagicMock(spec=Event)
    event.first_reported_at = datetime.now(UTC)
    assert event.first_reported_at.tzinfo is UTC


def test_relationship_counts_delegates_to_relationship_service() -> None:
    first = make_uuid()
    second = make_uuid()
    session = make_async_session(execute_all=[(first, second)])
    service = EventService(session)

    counts = run(service.relationship_counts([first, second]))

    assert counts == {first: 1, second: 1}
    session.execute.assert_awaited_once()
