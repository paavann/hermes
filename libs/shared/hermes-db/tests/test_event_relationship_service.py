"""Tests for hermes_db.services.event_relationship — EventRelationshipService."""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from conftest import make_async_session, make_uuid, run

from hermes_db.enums import EventRelationshipType
from hermes_db.models.event_relationship import EventRelationship
from hermes_db.services.event_relationship import (
    EventRelationshipService,
    RelationshipAnchorEvent,
    canonical_pair_key,
)


NOW = datetime(2026, 11, 20, 12, 0, 0, tzinfo=UTC)


def _anchor(
    *,
    event_id: uuid.UUID | None = None,
    embedding: tuple[float, ...] | None = (0.5, 0.5),
    embedding_model: str | None = "test-embed",
) -> RelationshipAnchorEvent:
    return RelationshipAnchorEvent(
        id=event_id or make_uuid(),
        ai_headline="Headline",
        ai_summary="Summary",
        category="TECHNOLOGY",
        country_code="CN",
        location_name="Beijing, China",
        latitude=39.9,
        longitude=116.4,
        event_time=NOW,
        latest_published_at=NOW,
        first_reported_at=NOW,
        importance_score=70.0,
        member_hash="mhash",
        version=1,
        embedding=embedding,
        embedding_model=embedding_model,
        entities=frozenset({"tiangong"}),
    )


def _event_row(
    *,
    event_id: uuid.UUID,
    headline: str = "Headline",
    entities_list: list[str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=event_id,
        ai_headline=headline,
        ai_summary="Summary",
        category="SCIENCE",
        country_code="PK",
        location_name="Islamabad, Pakistan",
        latitude=33.69,
        longitude=73.06,
        event_time=NOW,
        latest_published_at=NOW,
        first_reported_at=NOW,
        importance_score=55.0,
        member_hash="mhash",
        version=2,
        embedding=[0.4, 0.6],
        embedding_model="test-embed",
        entities_list=entities_list or [],
    )


class TestCanonicalPairKey:
    def test_orders_uuids_deterministically(self):
        left = uuid.UUID("00000000-0000-0000-0000-000000000001")
        right = uuid.UUID("00000000-0000-0000-0000-000000000002")
        assert canonical_pair_key(right, left) == (left, right)
        assert canonical_pair_key(left, right) == (left, right)


class TestRecallAndAnchors:
    def test_recent_anchor_events_hydrates_entities(self):
        event_id = make_uuid()
        row = _event_row(event_id=event_id)
        row.actors = [
            {
                "name": "  Israel ",
                "kind": "STATE",
                "role": "ACTOR",
                "location_name": "Israel",
                "country_code": "IL",
            }
        ]
        session = make_async_session(execute_all=[row])

        member = MagicMock()
        member.event_id = event_id
        member.entities = [{"name": " Zeeshan   Ali "}, {"name": "SUPARCO"}]

        with patch(
            "hermes_db.services.event_relationship.EventMembershipService"
        ) as membership_cls:
            membership_cls.return_value.current_members = AsyncMock(return_value=[member])
            svc = EventRelationshipService(session)
            anchors = run(svc.recent_anchor_events(since=NOW, limit=10))

        assert len(anchors) == 1
        assert anchors[0].id == event_id
        assert anchors[0].entities == frozenset({"zeeshan ali", "suparco"})
        assert anchors[0].actor_keys == frozenset({"israel"})
        assert anchors[0].actors[0]["country_code"] == "IL"

    def test_neighbor_candidates_skips_when_anchor_has_no_embedding(self):
        session = make_async_session()
        svc = EventRelationshipService(session)
        anchor = _anchor(embedding=None)

        assert run(svc.neighbor_candidates(anchor, since=NOW)) == []
        session.execute.assert_not_awaited()

    def test_neighbor_candidates_queries_without_country_veto(self):
        anchor = _anchor()
        neighbor_id = make_uuid()
        row = _event_row(event_id=neighbor_id)
        session = make_async_session(execute_all=[row])

        with patch(
            "hermes_db.services.event_relationship.EventMembershipService"
        ) as membership_cls:
            membership_cls.return_value.current_members = AsyncMock(return_value=[])
            svc = EventRelationshipService(session)
            neighbors = run(
                svc.neighbor_candidates(
                    anchor,
                    since=NOW,
                    min_embedding_sim=0.62,
                    limit=8,
                )
            )

        assert len(neighbors) == 1
        assert neighbors[0].id == neighbor_id
        stmt = session.execute.call_args.args[0]
        sql = str(stmt.compile())
        assert "country_code" not in sql.split("WHERE")[1]


class TestUpsertAndRead:
    def test_upsert_rejects_self_loop(self):
        session = make_async_session()
        svc = EventRelationshipService(session)
        event_id = make_uuid()

        with pytest.raises(ValueError, match="distinct"):
            run(
                svc.upsert_relationship(
                    source_event_id=event_id,
                    target_event_id=event_id,
                    relationship_type=EventRelationshipType.RELATED,
                    confidence=0.8,
                    rationale="Same event.",
                    pair_hash="hash",
                )
            )

    def test_upsert_inserts_new_relationship(self):
        session = make_async_session(execute_scalar_one_or_none=None)
        svc = EventRelationshipService(session)
        src = make_uuid()
        tgt = make_uuid()

        rel = run(
            svc.upsert_relationship(
                source_event_id=src,
                target_event_id=tgt,
                relationship_type=EventRelationshipType.REACTION,
                confidence=0.91,
                rationale="   Students gathered at SUPARCO to watch Zeeshan Ali.  ",
                pair_hash="hash-1",
            )
        )

        assert isinstance(rel, EventRelationship)
        assert rel.source_event_id == src
        assert rel.target_event_id == tgt
        assert rel.relationship_type == EventRelationshipType.REACTION
        assert rel.rationale == "Students gathered at SUPARCO to watch Zeeshan Ali."
        session.add.assert_called_once_with(rel)
        session.flush.assert_awaited_once()

    def test_upsert_updates_existing_even_when_direction_reverses(self):
        src = make_uuid()
        tgt = make_uuid()
        existing = EventRelationship(
            source_event_id=tgt,
            target_event_id=src,
            relationship_type=EventRelationshipType.RELATED,
            confidence=0.72,
            rationale="Initial link.",
            pair_hash="old-hash",
        )
        session = make_async_session(execute_scalar_one_or_none=existing)
        svc = EventRelationshipService(session)

        rel = run(
            svc.upsert_relationship(
                source_event_id=src,
                target_event_id=tgt,
                relationship_type=EventRelationshipType.CAUSED,
                confidence=0.88,
                rationale="Planes triggered alert.",
                pair_hash="new-hash",
            )
        )

        assert rel is existing
        assert existing.source_event_id == src
        assert existing.target_event_id == tgt
        assert existing.relationship_type == EventRelationshipType.CAUSED
        assert existing.confidence == 0.88
        assert existing.pair_hash == "new-hash"
        session.add.assert_not_called()
        session.flush.assert_awaited_once()

    def test_existing_pair_hashes_maps_canonical_keys(self):
        a = make_uuid()
        b = make_uuid()
        session = make_async_session(execute_all=[(b, a, "hash-ab")])
        svc = EventRelationshipService(session)

        result = run(svc.existing_pair_hashes([(a, b)]))

        assert result == {canonical_pair_key(a, b): "hash-ab"}

    def test_relationships_for_event_projects_direction(self):
        center = make_uuid()
        out_target = make_uuid()
        in_source = make_uuid()
        row_out = SimpleNamespace(
            id=make_uuid(),
            source_event_id=center,
            target_event_id=out_target,
            relationship_type=EventRelationshipType.REACTION.value,
            confidence=0.9,
            rationale="Watch party reacted to launch.",
            src_headline="Watch party",
            src_category="TECHNOLOGY",
            src_color="#00f0ff",
            src_location="Islamabad, Pakistan",
            src_lat=33.69,
            src_lng=73.06,
            src_score=28.0,
            src_time=NOW,
            tgt_headline="Boards Tiangong",
            tgt_category="SCIENCE",
            tgt_color="#a855f7",
            tgt_location="Beijing, China",
            tgt_lat=39.9,
            tgt_lng=116.4,
            tgt_score=40.0,
            tgt_time=NOW,
        )
        row_in = SimpleNamespace(
            id=make_uuid(),
            source_event_id=in_source,
            target_event_id=center,
            relationship_type=EventRelationshipType.CAUSED.value,
            confidence=0.85,
            rationale="Earlier briefing led to watch party.",
            src_headline="Briefing",
            src_category="SCIENCE",
            src_color="#a855f7",
            src_location="Beijing, China",
            src_lat=39.9,
            src_lng=116.4,
            src_score=32.0,
            src_time=NOW,
            tgt_headline="Watch party",
            tgt_category="TECHNOLOGY",
            tgt_color="#00f0ff",
            tgt_location="Islamabad, Pakistan",
            tgt_lat=33.69,
            tgt_lng=73.06,
            tgt_score=28.0,
            tgt_time=NOW,
        )
        session = make_async_session(execute_all=[row_out, row_in])
        svc = EventRelationshipService(session)

        views = run(svc.relationships_for_event(center))

        assert len(views) == 2
        assert views[0].direction == "OUTGOING"
        assert views[0].related_event_id == out_target
        assert views[0].related_latitude == 39.9
        assert views[1].direction == "INCOMING"
        assert views[1].related_event_id == in_source

    def test_relationships_for_event_ids_returns_map_edges(self):
        src = make_uuid()
        tgt = make_uuid()
        edge_id = make_uuid()
        row = SimpleNamespace(
            id=edge_id,
            source_event_id=src,
            target_event_id=tgt,
            relationship_type=EventRelationshipType.FOLLOW_UP.value,
            confidence=0.89,
            rationale="Embassy threat escalated into closure order.",
            src_headline="Threatens closure",
            src_category="POLITICS",
            src_color="#3b82f6",
            src_location="Pyongyang",
            src_lat=39.03,
            src_lng=125.76,
            tgt_headline="Orders closure",
            tgt_category="CONFLICT",
            tgt_color="#ef4444",
            tgt_location="Pyongyang",
            tgt_lat=39.03,
            tgt_lng=125.76,
        )
        session = make_async_session(execute_all=[row])
        svc = EventRelationshipService(session)

        edges = run(svc.relationships_for_event_ids([src]))

        assert len(edges) == 1
        assert edges[0].id == edge_id
        assert edges[0].relationship_type == EventRelationshipType.FOLLOW_UP
        assert edges[0].source_latitude == 39.03

    def test_counts_for_events_aggregates_both_directions(self):
        a = make_uuid()
        b = make_uuid()
        c = make_uuid()
        session = make_async_session(execute_all=[(a, b), (c, a)])
        svc = EventRelationshipService(session)

        counts = run(svc.counts_for_events([a, b]))

        assert counts == {a: 2, b: 1}
