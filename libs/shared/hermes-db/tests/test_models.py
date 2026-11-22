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

from sqlalchemy import CheckConstraint, String, inspect

from hermes_db.enums import (
    ArticleType,
    CredibilityTier,
    EventScope,
    EventStatus,
    EventTlStatus,
    ImpactLevel,
    IngestStatus,
    SelectionTier,
    SourceFeedProvider,
    SourceFetchPolicy,
    SourceType,
    ThreadKind,
    ThreadStatus,
    VerificationStatus,
)
from hermes_db.models.article import Article
from hermes_db.models.article_label import ArticleLabel
from hermes_db.models.event import Event
from hermes_db.models.event_tl import EventTl
from hermes_db.models.geocode_cache import GeocodeCache
from hermes_db.models.source import Source
from hermes_db.models.thread import Thread


# ---------------------------------------------------------------------------
# Article
# ---------------------------------------------------------------------------


class TestArticleModel:
    def test_tablename(self):
        assert Article.__tablename__ == "articles"

    def test_required_columns_present(self):
        cols = {c.name for c in inspect(Article).columns}
        required = {
            "id",
            "event_id",
            "source_id",
            "title",
            "url",
            "canonical_url",
            "canonical_url_hash",
            "duplicate_of_id",
            "feed_summary",
            "content_hash",
            "title_simhash",
            "body_simhash",
            "word_count",
            "body_source",
            "language",
            "ingest_status",
            "family_id",
            "claimed_at",
            "claimed_by",
            "attempt_count",
            "last_error",
            "embedding",
            "embedding_model",
            "embedding_input_hash",
        }
        assert required.issubset(cols)

    def test_claim_columns_default_to_unclaimed(self):
        cols = inspect(Article).columns

        assert cols["claimed_at"].nullable
        assert cols["claimed_by"].nullable
        assert cols["last_error"].nullable
        assert cols["attempt_count"].nullable is False
        assert cols["attempt_count"].default.arg == 0
        assert cols["attempt_count"].server_default.arg == "0"

    def test_analyzing_claim_index_is_partial(self):
        indexes = {index.name: index for index in Article.__table__.indexes}
        index = indexes["idx_articles_analyzing_claimed_at"]

        assert [col.name for col in index.columns] == ["claimed_at"]
        assert index.dialect_options["postgresql"]["where"] is not None

    def test_ledger_columns_are_nullable_before_normalization(self):
        cols = inspect(Article).columns
        for name in (
            "canonical_url",
            "feed_summary",
            "content_hash",
            "title_simhash",
            "body_simhash",
            "word_count",
            "body_source",
            "language",
        ):
            assert cols[name].nullable, f"{name} should be nullable"

    def test_title_simhash_is_hex_string(self):
        """A 64-bit SimHash is stored as a 16-char hex string to avoid overflow."""
        col = inspect(Article).columns["title_simhash"]
        assert isinstance(col.type, String)
        assert col.type.length == 16

    def test_ingest_status_default(self):
        col = inspect(Article).columns["ingest_status"]
        assert col.default is not None
        assert col.default.arg == IngestStatus.NEW
        assert col.server_default is not None
        assert col.server_default.arg == IngestStatus.NEW.value

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

    def test_event_id_is_nullable_and_sets_null_on_delete(self):
        col = inspect(Article).columns["event_id"]
        assert col.nullable
        fk = next(iter(col.foreign_keys))
        assert fk.ondelete == "SET NULL"

    def test_source_id_foreign_key(self):
        fks = inspect(Article).columns["source_id"].foreign_keys
        targets = {fk.target_fullname for fk in fks}
        assert "sources.id" in targets

    def test_source_id_is_nullable_and_sets_null_on_delete(self):
        col = inspect(Article).columns["source_id"]
        assert col.nullable
        fk = next(iter(col.foreign_keys))
        assert fk.ondelete == "SET NULL"

    def test_id_default_is_uuid4_callable(self):
        """id column default must be configured as the uuid4 callable."""
        col = inspect(Article).columns["id"]
        assert col.default is not None and col.default.is_callable
        assert isinstance(col.default.arg(None), uuid.UUID)

    def test_relationships_declared(self):
        """event, source, and label back-references must be mapped."""
        rels = {r.key for r in inspect(Article).relationships}
        assert "event" in rels
        assert "source" in rels
        assert "labels" in rels

    def test_labels_relationship_cascades(self):
        rel = inspect(Article).relationships["labels"]
        assert rel.passive_deletes is True
        assert rel.lazy == "raise"

    def test_embedding_columns_present(self):
        cols = inspect(Article).columns
        assert cols["embedding"].nullable
        assert cols["embedding_model"].nullable
        assert cols["embedding_input_hash"].nullable
        attrs = inspect(Article).column_attrs
        assert attrs["embedding"].deferred is True

    def test_embedding_index_is_hnsw(self):
        indexes = {index.name: index for index in Article.__table__.indexes}
        index = indexes["idx_articles_embedding"]
        assert index.dialect_options["postgresql"]["using"] == "hnsw"
        assert index.dialect_options["postgresql"]["with"] == {
            "m": 16,
            "ef_construction": 64,
        }

    def test_embedding_metadata_check_present(self):
        checks = {
            constraint.name
            for constraint in Article.__table__.constraints
            if isinstance(constraint, CheckConstraint)
        }
        assert "ck_articles_embedding_metadata" in checks

    def test_ledger_indexes_defined(self):
        indexes = {idx.name: idx for idx in Article.__table__.indexes}
        assert "idx_articles_content_hash" in indexes
        assert "idx_articles_canonical_url" in indexes
        assert "idx_articles_ingest_status_published_at" in indexes
        assert "idx_articles_event_id" in indexes
        assert "idx_articles_source_id" in indexes
        assert "uq_articles_canonical_url_hash" in indexes
        assert "idx_articles_duplicate_of_id" in indexes

    def test_canonical_url_hash_is_sha256_sized(self):
        col = inspect(Article).columns["canonical_url_hash"]
        assert col.nullable
        assert isinstance(col.type, String)
        assert col.type.length == 64

    def test_canonical_url_hash_index_is_partial_and_unique(self):
        indexes = {index.name: index for index in Article.__table__.indexes}
        index = indexes["uq_articles_canonical_url_hash"]

        assert index.unique is True
        assert [col.name for col in index.columns] == ["canonical_url_hash"]
        where = index.dialect_options["postgresql"]["where"]
        assert where is not None
        assert "duplicate_of_id IS NULL" in str(where)

    def test_duplicate_of_points_at_articles(self):
        col = inspect(Article).columns["duplicate_of_id"]
        assert col.nullable
        fk = next(iter(col.foreign_keys))
        assert fk.target_fullname == "articles.id"
        assert fk.ondelete == "SET NULL"


# ---------------------------------------------------------------------------
# ArticleLabel
# ---------------------------------------------------------------------------


class TestArticleLabelModel:
    def test_tablename(self):
        assert ArticleLabel.__tablename__ == "article_labels"

    def test_required_columns_present(self):
        cols = {c.name for c in inspect(ArticleLabel).columns}
        required = {
            "id",
            "article_id",
            "prompt_version",
            "model",
            "is_event",
            "article_type",
            "event_time",
            "severity",
            "scope",
            "confidence",
            "fact",
            "scale_facts",
            "entities",
            "locations",
            "labeled_at",
        }
        assert required.issubset(cols)

    def test_fact_is_nullable(self):
        assert inspect(ArticleLabel).columns["fact"].nullable

    def test_scale_facts_default_is_empty_dict(self):
        col = inspect(ArticleLabel).columns["scale_facts"]
        assert col.default is not None
        assert col.default.arg(None) == {}
        assert col.server_default is not None

    def test_article_id_foreign_key_cascades(self):
        fk = next(iter(inspect(ArticleLabel).columns["article_id"].foreign_keys))
        assert fk.target_fullname == "articles.id"
        assert fk.ondelete == "CASCADE"

    def test_article_prompt_version_is_unique(self):
        constraints = {c.name for c in ArticleLabel.__table__.constraints}
        assert "uq_article_labels_article_prompt" in constraints

    def test_severity_and_confidence_checks(self):
        constraints = {c.name for c in ArticleLabel.__table__.constraints}
        assert "ck_article_labels_severity_range" in constraints
        assert "ck_article_labels_confidence_range" in constraints

    def test_optional_label_fields_are_nullable(self):
        cols = inspect(ArticleLabel).columns
        for name in ("event_time", "severity", "scope", "confidence"):
            assert cols[name].nullable, f"{name} should be nullable"

    def test_article_type_default(self):
        col = inspect(ArticleLabel).columns["article_type"]
        assert col.default is not None
        assert col.default.arg == ArticleType.OTHER
        assert col.server_default is not None
        assert col.server_default.arg == ArticleType.OTHER.value

    def test_entities_and_locations_default_to_empty_lists(self):
        cols = inspect(ArticleLabel).columns
        for name in ("entities", "locations"):
            assert cols[name].default is not None
            assert cols[name].default.arg(None) == []

    def test_article_relationship(self):
        rel = inspect(ArticleLabel).relationships["article"]
        assert rel.lazy == "raise"

    def test_is_event_index_present(self):
        indexes = {idx.name for idx in ArticleLabel.__table__.indexes}
        assert "idx_article_labels_is_event_labeled" in indexes


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
            "impact_level",
            "article_count",
            "event_time",
            "latest_published_at",
            "thread_id",
            "importance_score",
            "score_breakdown",
            "score_version",
            "scored_at",
            "selection_tier",
            "selection_reason",
            "selected_at",
            "verification_status",
            "independent_origin_count",
            "source_count",
            "family_count",
            "first_seen_at",
            "last_member_added_at",
            "embedding_model",
            "locations",
            "merged_into_id",
            "merged_at",
            "merge_reason",
            "member_hash",
            "version",
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

    def test_impact_level_default(self):
        """impact_level column default must be ImpactLevel.MODERATE."""
        col = inspect(Event).columns["impact_level"]
        assert col.default is not None
        assert col.default.arg == ImpactLevel.MODERATE
        assert col.server_default is not None

    def test_article_count_default(self):
        """article_count column default must be 0."""
        col = inspect(Event).columns["article_count"]
        assert col.default is not None
        assert col.default.arg == 0

    def test_event_time_and_latest_published_are_nullable(self):
        cols = inspect(Event).columns
        assert cols["event_time"].nullable
        assert cols["latest_published_at"].nullable

    def test_thread_id_is_nullable_and_sets_null_on_delete(self):
        col = inspect(Event).columns["thread_id"]
        assert col.nullable
        fk = next(iter(col.foreign_keys))
        assert fk.target_fullname == "threads.id"
        assert fk.ondelete == "SET NULL"

    def test_importance_defaults_to_zero(self):
        cols = inspect(Event).columns
        assert cols["importance_score"].default is not None
        assert cols["importance_score"].default.arg == 0.0
        assert cols["importance_score"].server_default is not None

    def test_selection_tier_default(self):
        col = inspect(Event).columns["selection_tier"]
        assert col.default is not None
        assert col.default.arg == SelectionTier.FILLER
        assert col.server_default is not None
        assert col.server_default.arg == SelectionTier.FILLER.value

    def test_verification_status_default(self):
        col = inspect(Event).columns["verification_status"]
        assert col.default is not None
        assert col.default.arg == VerificationStatus.UNVERIFIED
        assert col.server_default is not None
        assert col.server_default.arg == VerificationStatus.UNVERIFIED.value

    def test_independent_origin_count_default(self):
        col = inspect(Event).columns["independent_origin_count"]
        assert col.default is not None
        assert col.default.arg == 0
        assert col.server_default is not None

    def test_member_hash_is_nullable(self):
        assert inspect(Event).columns["member_hash"].nullable

    def test_version_default(self):
        col = inspect(Event).columns["version"]
        assert col.default is not None
        assert col.default.arg == 1
        assert col.server_default is not None

    def test_event_graph_relationships(self):
        rels = {r.key for r in inspect(Event).relationships}
        assert "thread" in rels

    def test_articles_relationship(self):
        rel = inspect(Event).relationships["articles"]
        assert rel.passive_deletes is True
        assert rel.lazy == "raise"

    def test_indexes_defined(self):
        """The gist, hnsw, composite status/updated, and partial indexes must exist."""
        indexes = {idx.name: idx for idx in Event.__table__.indexes}
        assert "idx_events_location" in indexes
        assert "idx_events_embedding" in indexes
        assert "idx_events_active_importance" in indexes
        assert "idx_events_scope" in indexes
        assert "idx_events_status_last_updated" in indexes
        assert "idx_events_country" in indexes
        assert "idx_events_thread_id" in indexes
        assert "idx_events_event_time" in indexes
        assert "idx_events_latest_published_at" in indexes
        assert "idx_events_active_selection" in indexes
        assert "idx_events_merge_candidates" in indexes

        hnsw = indexes["idx_events_embedding"]
        assert hnsw.dialect_options["postgresql"]["with"] == {
            "m": 16,
            "ef_construction": 64,
        }


# ---------------------------------------------------------------------------
# Thread
# ---------------------------------------------------------------------------


class TestThreadModel:
    def test_tablename(self):
        assert Thread.__tablename__ == "threads"

    def test_required_columns_present(self):
        cols = {c.name for c in inspect(Thread).columns}
        required = {
            "id",
            "kind",
            "name",
            "description",
            "status",
            "started_at",
            "ended_at",
            "entities",
            "keywords",
            "importance",
            "name_norm",
            "event_count",
            "last_event_at",
            "embedding",
            "embedding_model",
        }
        assert required.issubset(cols)

    def test_kind_default(self):
        col = inspect(Thread).columns["kind"]
        assert col.default is not None
        assert col.default.arg == ThreadKind.DEVELOPING
        assert col.server_default is not None
        assert col.server_default.arg == ThreadKind.DEVELOPING.value

    def test_status_default(self):
        col = inspect(Thread).columns["status"]
        assert col.default is not None
        assert col.default.arg == ThreadStatus.ACTIVE
        assert col.server_default is not None
        assert col.server_default.arg == ThreadStatus.ACTIVE.value

    def test_optional_fields_are_nullable(self):
        cols = inspect(Thread).columns
        for name in ("description", "started_at", "ended_at", "last_event_at"):
            assert cols[name].nullable, f"{name} should be nullable"

    def test_importance_default(self):
        col = inspect(Thread).columns["importance"]
        assert col.default is not None
        assert col.default.arg == 0.0
        assert col.server_default is not None

    def test_json_defaults_are_empty_lists(self):
        cols = inspect(Thread).columns
        for name in ("entities", "keywords"):
            assert cols[name].default is not None
            assert cols[name].default.arg(None) == []

    def test_events_relationship(self):
        rel = inspect(Thread).relationships["events"]
        assert rel.passive_deletes is True
        assert rel.lazy == "raise"

    def test_indexes_defined(self):
        indexes = {idx.name for idx in Thread.__table__.indexes}
        assert "idx_threads_status_importance" in indexes
        assert "idx_threads_kind_status" in indexes
        assert "idx_threads_status_last_event" in indexes
        assert "idx_threads_name_norm" in indexes
        assert "idx_threads_embedding" in indexes


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
        required = {
            "id",
            "name",
            "slug",
            "url",
            "feed_url",
            "fallback_feed_url",
            "feed_provider",
            "canonical_domain",
            "paywall",
            "fetch_policy",
            "source_type",
            "credibility",
            "is_active",
            "origin_group",
            "country_code",
            "language",
            "last_error",
            "consecutive_failures",
        }
        assert required.issubset(cols)

    def test_origin_identity_fields_are_nullable(self):
        cols = inspect(Source).columns
        for name in ("origin_group", "country_code", "language", "last_error"):
            assert cols[name].nullable, f"{name} should be nullable"

    def test_consecutive_failures_default(self):
        col = inspect(Source).columns["consecutive_failures"]
        assert col.default is not None
        assert col.default.arg == 0
        assert col.server_default is not None
        assert col.server_default.arg == "0"

    def test_slug_is_unique(self):
        col = inspect(Source).columns["slug"]
        assert col.unique

    def test_feed_url_is_nullable(self):
        col = inspect(Source).columns["feed_url"]
        assert col.nullable

    def test_fallback_feed_url_is_nullable(self):
        col = inspect(Source).columns["fallback_feed_url"]
        assert col.nullable

    def test_feed_provider_default(self):
        col = inspect(Source).columns["feed_provider"]
        assert col.default is not None
        assert col.default.arg == SourceFeedProvider.PUBLISHER
        assert col.server_default is not None
        assert col.server_default.arg == SourceFeedProvider.PUBLISHER.value

    def test_fetch_policy_default(self):
        col = inspect(Source).columns["fetch_policy"]
        assert col.default is not None
        assert col.default.arg == SourceFetchPolicy.FULL_TEXT
        assert col.server_default is not None
        assert col.server_default.arg == SourceFetchPolicy.FULL_TEXT.value

    def test_paywall_defaults_to_false(self):
        col = inspect(Source).columns["paywall"]
        assert col.default is not None
        assert col.default.arg is False
        assert col.server_default is not None

    def test_canonical_domain_is_nullable(self):
        assert inspect(Source).columns["canonical_domain"].nullable

    def test_canonical_domain_index_present(self):
        indexes = {idx.name for idx in Source.__table__.indexes}
        assert "idx_sources_canonical_domain" in indexes

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
        assert "health" not in rels

    def test_origin_group_index_present(self):
        indexes = {idx.name: idx for idx in Source.__table__.indexes}
        assert "idx_sources_origin_group" in indexes
        where = (
            indexes["idx_sources_origin_group"]
            .dialect_options["postgresql"]
            .get("where")
        )
        assert where is not None

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

        for name in (
            "Article",
            "ArticleLabel",
            "Event",
            "EventTl",
            "Source",
            "Thread",
            "GeocodeCache",
        ):
            assert hasattr(models, name), f"{name} not exported from hermes_db.models"

    def test_exported_names_are_orm_classes(self):
        from hermes_db import models

        for name in (
            "Article",
            "ArticleLabel",
            "Event",
            "EventTl",
            "Source",
            "Thread",
            "GeocodeCache",
        ):
            cls = getattr(models, name)
            # Every model must be registered in Base.metadata.
            assert cls.__tablename__ in {
                t
                for t in [
                    "articles",
                    "article_labels",
                    "events",
                    "event_timelines",
                    "sources",
                    "threads",
                    "geocode_cache",
                ]
            }
