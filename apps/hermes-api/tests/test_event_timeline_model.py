"""Tests for the EventTimeline model.

These tests validate the model's default values and field constraints
entirely in-memory without touching the database.
"""

import uuid

from hermes_api.db.models.event_timeline import EventTimeline


def _make_timeline(**kwargs) -> EventTimeline:
    """Instantiate an EventTimeline with sane defaults for testing."""
    defaults: dict = {
        "id": uuid.uuid4(),
        "event_id": uuid.uuid4(),
        "nodes": [],
        "edges": [],
        "topic_summary": "",
        "gdelt_row_count": 0,
        "needs_refresh": False,
    }
    defaults.update(kwargs)
    timeline = EventTimeline()
    for key, value in defaults.items():
        setattr(timeline, key, value)
    return timeline


class TestEventTimelineDefaults:
    """Validate that default field values are correct."""

    def test_nodes_default_is_empty_list(self) -> None:
        """nodes should default to an empty list."""
        t = _make_timeline()
        assert t.nodes == []

    def test_edges_default_is_empty_list(self) -> None:
        """edges should default to an empty list."""
        t = _make_timeline()
        assert t.edges == []

    def test_needs_refresh_default_is_false(self) -> None:
        """needs_refresh should default to False."""
        t = _make_timeline()
        assert t.needs_refresh is False

    def test_gdelt_row_count_default_is_zero(self) -> None:
        """gdelt_row_count should default to 0."""
        t = _make_timeline()
        assert t.gdelt_row_count == 0

    def test_topic_summary_default_is_empty_string(self) -> None:
        """topic_summary should default to an empty string."""
        t = _make_timeline()
        assert t.topic_summary == ""


class TestEventTimelineFields:
    """Validate that field assignments are stored correctly."""

    def test_stores_nodes_as_list(self) -> None:
        """nodes field should accept and store a list of dicts."""
        nodes = [
            {
                "id": "node_1",
                "headline": "Gaza ceasefire talks begin",
                "latitude": 31.5,
                "longitude": 34.5,
            }
        ]
        t = _make_timeline(nodes=nodes)
        assert t.nodes == nodes
        assert t.nodes[0]["id"] == "node_1"

    def test_stores_edges_as_list(self) -> None:
        """edges field should accept and store a list of dicts."""
        edges = [{"source": "node_1", "target": "node_2", "label": "led to"}]
        t = _make_timeline(edges=edges)
        assert t.edges == edges
        assert t.edges[0]["source"] == "node_1"

    def test_needs_refresh_can_be_set_true(self) -> None:
        """needs_refresh should accept True when the ingestion pipeline flags it."""
        t = _make_timeline(needs_refresh=True)
        assert t.needs_refresh is True

    def test_gdelt_row_count_stores_integer(self) -> None:
        """gdelt_row_count should store a positive integer."""
        t = _make_timeline(gdelt_row_count=42)
        assert t.gdelt_row_count == 42

    def test_event_id_stored_correctly(self) -> None:
        """event_id FK should be stored as a UUID."""
        eid = uuid.uuid4()
        t = _make_timeline(event_id=eid)
        assert t.event_id == eid

    def test_table_name(self) -> None:
        """The ORM table name must match the migration."""
        assert EventTimeline.__tablename__ == "event_timelines"


class TestEventTimelineRelationship:
    """Validate the back-reference relationship attribute exists on Event."""

    def test_event_has_timeline_attribute(self) -> None:
        """Event should expose a 'timeline' attribute for the back-reference."""
        from hermes_api.db.models.event import Event

        assert hasattr(Event, "timeline"), (
            "Event model is missing the 'timeline' relationship attribute. "
            "The back-reference to EventTimeline was not added correctly."
        )

    def test_event_timeline_has_event_attribute(self) -> None:
        """EventTimeline should expose an 'event' attribute for the back-reference."""
        assert hasattr(EventTimeline, "event"), (
            "EventTimeline model is missing the 'event' relationship attribute."
        )
