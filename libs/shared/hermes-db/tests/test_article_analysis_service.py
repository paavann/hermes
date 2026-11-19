"""Tests for hermes_db.services.article_analysis — ArticleAnalysisService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from conftest import make_async_session, make_uuid, run

from hermes_db.enums import (
    ArticleBodySource,
    IngestStatus,
    RejectStage,
    SourceFetchPolicy,
)
from hermes_db.models.article import Article
from hermes_db.services.article_analysis import ArticleAnalysisService


NOW = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


def _article_mock(
    *,
    source: MagicMock | None = None,
    family_id=None,
) -> MagicMock:
    article = MagicMock(spec=Article)
    article.id = make_uuid()
    article.title = "Earthquake strikes coastal city"
    article.url = "https://news.example.com/story"
    article.feed_summary = "A summary."
    article.published_at = NOW
    article.language = "en"
    article.attempt_count = 0
    article.family_id = family_id
    article.source = source
    return article


class TestLoadForAnalysis:
    def test_maps_source_policy_and_fields(self):
        source = MagicMock()
        source.name = "Example News"
        source.slug = "example-news"
        source.origin_group = "example"
        source.fetch_policy = SourceFetchPolicy.FULL_TEXT
        source.paywall = False
        article = _article_mock(source=source)
        session = make_async_session(execute_scalars=[article])

        snapshots = run(
            ArticleAnalysisService(session).load_for_analysis([article.id])
        )

        assert len(snapshots) == 1
        snapshot = snapshots[0]
        assert snapshot.id == article.id
        assert snapshot.source_name == "Example News"
        assert snapshot.source_slug == "example-news"
        assert snapshot.source_origin_group == "example"
        assert snapshot.fetch_policy == SourceFetchPolicy.FULL_TEXT
        assert snapshot.paywall is False

    def test_defaults_to_summary_only_when_source_missing(self):
        article = _article_mock(source=None)
        session = make_async_session(execute_scalars=[article])

        snapshots = run(
            ArticleAnalysisService(session).load_for_analysis([article.id])
        )

        assert snapshots[0].fetch_policy == SourceFetchPolicy.SUMMARY_ONLY
        assert snapshots[0].paywall is True

    def test_empty_input_does_not_query(self):
        session = make_async_session()

        assert run(ArticleAnalysisService(session).load_for_analysis([])) == []
        session.execute.assert_not_awaited()


class TestSaveText:
    def test_updates_fingerprints_and_fetch_fields(self):
        article_id = make_uuid()
        session = make_async_session()

        run(
            ArticleAnalysisService(session).save_text(
                article_id,
                body_source=ArticleBodySource.FULL_TEXT,
                body_simhash="b" * 16,
                title_simhash="a" * 16,
                word_count=420,
                input_quality=0.82,
                fetch_http_status=200,
            )
        )

        stmt = session.execute.call_args.args[0]
        params = stmt.compile().params
        assert params["body_source"] == ArticleBodySource.FULL_TEXT
        assert params["body_simhash"] == "b" * 16
        assert params["title_simhash"] == "a" * 16
        assert params["word_count"] == 420
        assert params["input_quality"] == 0.82
        assert params["fetch_http_status"] == 200


class TestSaveEmbedding:
    def test_upserts_current_embedding(self):
        article_id = make_uuid()
        session = make_async_session()

        run(
            ArticleAnalysisService(session).save_embedding(
                article_id,
                model="test/embed",
                embedding=[0.1, 0.2, 0.3],
                input_hash="c" * 64,
            )
        )

        stmt = session.execute.call_args.args[0]
        params = stmt.compile().params
        assert params["embedding_model"] == "test/embed"
        assert params["embedding_input_hash"] == "c" * 64
        assert list(params["embedding"]) == [0.1, 0.2, 0.3]


class TestFinalize:
    def test_rejected_sets_reason_and_timestamp(self):
        article_id = make_uuid()
        session = make_async_session()

        run(
            ArticleAnalysisService(session).finalize(
                article_id,
                status=IngestStatus.REJECTED,
                reject_stage=RejectStage.GATE,
                reject_reason="low_specificity_2",
            )
        )

        stmt = session.execute.call_args.args[0]
        params = stmt.compile().params
        assert params["ingest_status"] == IngestStatus.REJECTED
        assert params["reject_stage"] == RejectStage.GATE
        assert params["reject_reason"] == "low_specificity_2"
        assert params["claimed_at"] is None
        assert params["claimed_by"] is None

    def test_accepted_clears_reject_fields(self):
        article_id = make_uuid()
        session = make_async_session()

        run(
            ArticleAnalysisService(session).finalize(
                article_id,
                status=IngestStatus.LABELED,
            )
        )

        stmt = session.execute.call_args.args[0]
        params = stmt.compile().params
        assert params["ingest_status"] == IngestStatus.LABELED
        assert params["reject_stage"] is None
        assert params["reject_reason"] is None
        assert params["rejected_at"] is None
