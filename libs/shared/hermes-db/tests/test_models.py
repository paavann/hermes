"""Tests for hermes_db.models — ORM model definitions.

These tests operate entirely at the SQLAlchemy mapper / metadata layer and
do **not** require a live database connection.  We inspect:

* ``__tablename__`` declarations
* Required vs. optional (nullable) columns
* Foreign-key relationships
* Index presence
* Enum column types
* Model-level Python defaults
"""

import uuid

from sqlalchemy import inspect

from hermes_db.enums import (
    CredibilityTier,
    EventScope,
    EventStatus,
    EventTlStatus,
    SourceType,
)
from hermes_db.models.article import Article
from hermes_db.models.event import Event
from hermes_db.models.event_tl import EventTl
from hermes_db.models.geocode_cache import GeocodeCache
from hermes_db.models.source import Source


# ---------------------------------------------------------------------------
# Article
# ---------------------------------------------------------------------------


class TestArticleModel:
    def test_tablename(self):
        assert Article.__tablename__ == "articles"

    def test_required_columns_present(self):
        cols = {c.name for c in inspect(Article).columns}
        required = {"id", "event_id", "source_id", "title", "url"}
        assert required.issubset(cols)

    def test_url_is_unique(self):
        col = inspect(Article).columns["url"]
        assert col.unique

    def test_thumbnail_url_is_nullable(self):
        col = inspect(Article).columns["thumbnail_url"]
        assert col.nullable

    def test_published_at_is_nullable(self):
        col = inspect(Article).columns["published_at"]
        assert col.nullable

    def test_event_id_foreign_key(self):
        fks = inspect(Article).columns["event_id"].foreign_keys
        targets = {fk.target_fullname for fk in fks}
        assert "events.id" in targets

    def test_source_id_foreign_key(self):
        fks = inspect(Article).columns["source_id"].foreign_keys
        targets = {fk.target_fullname for fk in fks}
        assert "sources.id" in targets

    def test_id_default_is_uuid4_callable(self):
        """id column default must be configured as the uuid4 callable."""
        col = inspect(Article).columns["id"]
        assert col.default is not None and col.default.is_callable
        assert isinstance(col.default.arg(None), uuid.UUID)

    def test_relationships_declared(self):
        """event and source back-references must be mapped."""
        rels = {r.key for r in inspect(Article).relationships}
        assert "event" in rels
        assert "source" in rels


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------


class TestEventModel:
    def test_tablename(self):
        assert Event.__tablename__ == "events"

    def test_required_columns_present(self):
        cols = {c.name for c in inspect(Event).columns}
        required = {
            "id",
            "ai_headline",
            "category",
            "category_color",
            "status",
            "scope",
            "trending_score",
            "article_count",
        }
        assert required.issubset(cols)

    def test_location_is_nullable(self):
        col = inspect(Event).columns["location"]
        assert col.nullable

    def test_location_name_is_nullable(self):
        col = inspect(Event).columns["location_name"]
        assert col.nullable

    def test_country_code_is_nullable(self):
        col = inspect(Event).columns["country_code"]
        assert col.nullable

    def test_ai_summary_is_nullable(self):
        col = inspect(Event).columns["ai_summary"]
        assert col.nullable

    def test_embedding_column_present(self):
        cols = {c.name for c in inspect(Event).columns}
        assert "embedding" in cols

    def test_status_default(self):
        """status column default must be EventStatus.ACTIVE."""
        col = inspect(Event).columns["status"]
        assert col.default is not None
        assert col.default.arg == EventStatus.ACTIVE

    def test_scope_default(self):
        """scope column default must be EventScope.COUNTRY."""
        col = inspect(Event).columns["scope"]
        assert col.default is not None
        assert col.default.arg == EventScope.COUNTRY

    def test_trending_score_default(self):
        """trending_score column default must be 0.0."""
        col = inspect(Event).columns["trending_score"]
        assert col.default is not None
        assert col.default.arg == 0.0

    def test_article_count_default(self):
        """article_count column default must be 0."""
        col = inspect(Event).columns["article_count"]
        assert col.default is not None
        assert col.default.arg == 0

    def test_articles_relationship(self):
        rels = {r.key for r in inspect(Event).relationships}
        assert "articles" in rels

    def test_indexes_defined(self):
        """The gist, hnsw, and partial indexes must exist in __table_args__."""
        index_names = {idx.name for idx in Event.__table__.indexes}
        assert "idx_events_location" in index_names
        assert "idx_events_embedding" in index_names
        assert "idx_events_active_score" in index_names
        assert "idx_events_scope" in index_names
        assert "idx_events_country" in index_names


# ---------------------------------------------------------------------------
# EventTl
# ---------------------------------------------------------------------------


class TestEventTlModel:
    def test_tablename(self):
        assert EventTl.__tablename__ == "event_timelines"

    def test_required_columns_present(self):
        cols = {c.name for c in inspect(EventTl).columns}
        required = {"id", "event_id", "status", "nodes", "edges", "tl_summary"}
        assert required.issubset(cols)

    def test_event_id_foreign_key(self):
        fks = inspect(EventTl).columns["event_id"].foreign_keys
        targets = {fk.target_fullname for fk in fks}
        assert "events.id" in targets

    def test_event_id_is_unique(self):
        """event_id must be unique — each event has at most one timeline."""
        col = inspect(EventTl).columns["event_id"]
        assert col.unique

    def test_status_default(self):
        """status column default must be EventTlStatus.GENERATING."""
        col = inspect(EventTl).columns["status"]
        assert col.default is not None
        assert col.default.arg == EventTlStatus.GENERATING

    def test_nodes_default_is_list(self):
        """nodes column default must be the list factory."""
        col = inspect(EventTl).columns["nodes"]
        assert col.default is not None
        # SQLAlchemy wraps the callable so we must invoke it with a context arg.
        assert col.default.arg(None) == []

    def test_edges_default_is_list(self):
        """edges column default must be the list factory."""
        col = inspect(EventTl).columns["edges"]
        assert col.default is not None
        assert col.default.arg(None) == []

    def test_tl_summary_default_is_empty_string(self):
        """tl_summary column default must be empty string."""
        col = inspect(EventTl).columns["tl_summary"]
        assert col.default is not None
        assert col.default.arg == ""

    def test_page_count_default(self):
        """page_count column default must be 0."""
        col = inspect(EventTl).columns["page_count"]
        assert col.default is not None
        assert col.default.arg == 0

    def test_node_count_default(self):
        """node_count column default must be 0."""
        col = inspect(EventTl).columns["node_count"]
        assert col.default is not None
        assert col.default.arg == 0

    def test_wikipedia_title_is_nullable(self):
        col = inspect(EventTl).columns["wikipedia_title"]
        assert col.nullable

    def test_generated_at_is_nullable(self):
        col = inspect(EventTl).columns["generated_at"]
        assert col.nullable

    def test_id_default_is_uuid4_callable(self):
        """id column default must be configured as the uuid4 callable."""
        col = inspect(EventTl).columns["id"]
        assert col.default is not None and col.default.is_callable
        assert isinstance(col.default.arg(None), uuid.UUID)


# ---------------------------------------------------------------------------
# GeocodeCache
# ---------------------------------------------------------------------------


class TestGeocodeCacheModel:
    def test_tablename(self):
        assert GeocodeCache.__tablename__ == "geocode_cache"

    def test_required_columns_present(self):
        cols = {c.name for c in inspect(GeocodeCache).columns}
        required = {"id", "location_name", "latitude", "longitude"}
        assert required.issubset(cols)

    def test_location_name_is_unique(self):
        col = inspect(GeocodeCache).columns["location_name"]
        assert col.unique

    def test_latitude_is_nullable(self):
        col = inspect(GeocodeCache).columns["latitude"]
        assert col.nullable

    def test_longitude_is_nullable(self):
        col = inspect(GeocodeCache).columns["longitude"]
        assert col.nullable

    def test_display_name_is_nullable(self):
        col = inspect(GeocodeCache).columns["display_name"]
        assert col.nullable

    def test_id_default_is_uuid4_callable(self):
        """id column default must be configured as the uuid4 callable."""
        col = inspect(GeocodeCache).columns["id"]
        assert col.default is not None and col.default.is_callable
        assert isinstance(col.default.arg(None), uuid.UUID)

    def test_created_at_has_server_default(self):
        col = inspect(GeocodeCache).columns["created_at"]
        assert col.server_default is not None


# ---------------------------------------------------------------------------
# Source
# ---------------------------------------------------------------------------


class TestSourceModel:
    def test_tablename(self):
        assert Source.__tablename__ == "sources"

    def test_required_columns_present(self):
        cols = {c.name for c in inspect(Source).columns}
        required = {"id", "name", "slug", "url", "source_type", "credibility", "is_active"}
        assert required.issubset(cols)

    def test_slug_is_unique(self):
        col = inspect(Source).columns["slug"]
        assert col.unique

    def test_feed_url_is_nullable(self):
        col = inspect(Source).columns["feed_url"]
        assert col.nullable

    def test_logo_url_is_nullable(self):
        col = inspect(Source).columns["logo_url"]
        assert col.nullable

    def test_last_fetched_at_is_nullable(self):
        col = inspect(Source).columns["last_fetched_at"]
        assert col.nullable

    def test_source_type_default(self):
        """source_type column default must be SourceType.RSS."""
        col = inspect(Source).columns["source_type"]
        assert col.default is not None
        assert col.default.arg == SourceType.RSS

    def test_credibility_default(self):
        """credibility column default must be CredibilityTier.TIER_3."""
        col = inspect(Source).columns["credibility"]
        assert col.default is not None
        assert col.default.arg == CredibilityTier.TIER_3

    def test_is_active_default(self):
        """is_active column default must be True."""
        col = inspect(Source).columns["is_active"]
        assert col.default is not None
        assert col.default.arg is True

    def test_fetch_interval_default(self):
        """fetch_interval_minutes column default must be 15."""
        col = inspect(Source).columns["fetch_interval_minutes"]
        assert col.default is not None
        assert col.default.arg == 15

    def test_articles_relationship(self):
        rels = {r.key for r in inspect(Source).relationships}
        assert "articles" in rels

    def test_id_default_is_uuid4_callable(self):
        """id column default must be configured as the uuid4 callable."""
        col = inspect(Source).columns["id"]
        assert col.default is not None and col.default.is_callable
        assert isinstance(col.default.arg(None), uuid.UUID)


# ---------------------------------------------------------------------------
# models/__init__.py — public surface
# ---------------------------------------------------------------------------


class TestModelsPackage:
    def test_all_models_exported(self):
        from hermes_db import models

        for name in ("Article", "Event", "EventTl", "Source", "GeocodeCache"):
            assert hasattr(models, name), f"{name} not exported from hermes_db.models"

    def test_exported_names_are_orm_classes(self):
        from hermes_db import models

        for name in ("Article", "Event", "EventTl", "Source", "GeocodeCache"):
            cls = getattr(models, name)
            # Every model must be registered in Base.metadata.
            assert cls.__tablename__ in {
                t for t in ["articles", "events", "event_timelines", "sources", "geocode_cache"]
            }
