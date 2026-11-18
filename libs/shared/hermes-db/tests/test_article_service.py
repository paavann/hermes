"""Tests for hermes_db.services.article — ArticleService.

All tests use a mocked AsyncSession so no database is involved.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from conftest import make_async_session, make_uuid, run
from sqlalchemy.engine import CursorResult

from hermes_db.enums import IngestStatus
from hermes_db.models.article import Article
from hermes_db.services.article import ArticleService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def session_url_exists(request) -> AsyncMock:
    """Session mock pre-configured for article_url_exists.

    The ``request.param`` boolean controls what scalar_one_or_none returns:
    - True  → an article UUID (URL already exists)
    - False → None (URL is new)
    """
    existing = request.param
    return make_async_session(
        execute_scalar_one_or_none=make_uuid() if existing else None
    )


# ---------------------------------------------------------------------------
# article_url_exists
# ---------------------------------------------------------------------------


class TestArticleUrlExists:
    @pytest.mark.parametrize(
        "session_url_exists,expected",
        [(True, True), (False, False)],
        indirect=["session_url_exists"],
    )
    def test_returns_correct_bool(self, session_url_exists, expected):
        """Should return True when the URL is already in the DB, False otherwise."""
        svc = ArticleService(session_url_exists)
        result = run(svc.article_url_exists("https://example.com/article"))
        assert result is expected

    def test_executes_exactly_one_query(self):
        """Should issue exactly one SELECT to the DB."""
        session = make_async_session(execute_scalar_one_or_none=None)
        svc = ArticleService(session)
        run(svc.article_url_exists("https://example.com/article"))
        session.execute.assert_awaited_once()

    def test_url_not_exists_returns_false(self):
        session = make_async_session(execute_scalar_one_or_none=None)
        svc = ArticleService(session)
        assert run(svc.article_url_exists("https://new-url.com")) is False

    def test_url_exists_returns_true(self):
        session = make_async_session(execute_scalar_one_or_none=make_uuid())
        svc = ArticleService(session)
        assert run(svc.article_url_exists("https://existing.com")) is True


# ---------------------------------------------------------------------------
# create_article
# ---------------------------------------------------------------------------


class TestCreateArticle:
    def _make_svc(
        self, *, returned_article: Article | None = None
    ) -> tuple[ArticleService, AsyncMock]:
        """Build a service backed by a session mock.

        ``returned_article`` is what ``execute(...).scalar_one_or_none()`` yields,
        simulating the RETURNING clause on the pg upsert.
        """
        session = make_async_session(execute_scalar_one_or_none=returned_article)
        return ArticleService(session), session

    def test_returns_article_instance(self):
        """create_article must return the Article returned by the upsert RETURNING clause."""
        mock_article = MagicMock(spec=Article)
        svc, _ = self._make_svc(returned_article=mock_article)
        result = run(
            svc.create_article(
                event_id=make_uuid(),
                source_id=make_uuid(),
                title="Test title",
                url="https://example.com/article-1",
            )
        )
        assert result is mock_article

    def test_returns_none_on_duplicate_url(self):
        """When the upsert hits ON CONFLICT DO NOTHING, RETURNING yields nothing → None."""
        svc, _ = self._make_svc(returned_article=None)
        result = run(
            svc.create_article(
                event_id=make_uuid(),
                source_id=make_uuid(),
                title="Dupe",
                url="https://example.com/duplicate",
            )
        )
        assert result is None

    def test_executes_exactly_one_query(self):
        """create_article must issue exactly one execute (the upsert INSERT ... RETURNING)."""
        svc, session = self._make_svc()
        run(
            svc.create_article(
                event_id=make_uuid(),
                source_id=make_uuid(),
                title="Title",
                url="https://example.com/x",
            )
        )
        session.execute.assert_awaited_once()

    def test_does_not_call_session_add(self):
        """Upsert path must not call session.add() — that was the old plain-insert approach."""
        svc, session = self._make_svc()
        run(
            svc.create_article(
                event_id=make_uuid(),
                source_id=make_uuid(),
                title="T",
                url="https://example.com/y",
            )
        )
        session.add.assert_not_called()

    def test_published_at_defaults_to_none_on_new_article(self):
        """When published_at is omitted the article returned from DB should be unchanged."""
        mock_article = MagicMock(spec=Article)
        mock_article.published_at = None
        svc, _ = self._make_svc(returned_article=mock_article)
        article = run(
            svc.create_article(
                event_id=make_uuid(),
                source_id=make_uuid(),
                title="No date",
                url="https://example.com/no-date",
            )
        )
        assert article.published_at is None

    def test_article_id_column_default_is_uuid4(self):
        """The Article.id column default must be configured as the uuid4 callable.

        SQLAlchemy 2.x mapped_column(default=uuid.uuid4) registers a
        ColumnDefault that fires at INSERT time, not at __init__ time.
        We verify the metadata rather than the transient instance value.
        """
        from sqlalchemy import inspect

        from hermes_db.models.article import Article

        col = inspect(Article).columns["id"]
        assert col.default is not None and col.default.is_callable
        assert isinstance(col.default.arg(None), uuid.UUID)


# ---------------------------------------------------------------------------
# create_article — ledger extensions
# ---------------------------------------------------------------------------


def _make_cursor_result(rowcount: int) -> MagicMock:
    result = MagicMock(spec=CursorResult)
    result.rowcount = rowcount
    return result


class TestCreateLedgerArticle:
    def test_event_and_source_are_optional(self):
        """Ledger inserts must not require event or source membership."""
        mock_article = MagicMock(spec=Article)
        session = make_async_session(execute_scalar_one_or_none=mock_article)
        svc = ArticleService(session)

        result = run(
            svc.create_article(
                title="Ledger article",
                url="https://example.com/ledger",
            )
        )

        assert result is mock_article

    def test_ledger_fields_are_stored(self):
        """Feed summary and URL identity fields must reach the insert."""
        session = make_async_session(execute_scalar_one_or_none=MagicMock(spec=Article))
        svc = ArticleService(session)

        run(
            svc.create_article(
                title="Ledger article",
                url="https://example.com/ledger",
                source_id=make_uuid(),
                canonical_url="https://example.com/ledger?ref=rss",
                canonical_url_hash="d" * 64,
                thumbnail_url="https://example.com/ledger.jpg",
                feed_summary="Feed summary",
                content_hash="a" * 64,
                title_simhash="0123456789abcdef",
                language="en",
            )
        )

        stmt = session.execute.call_args.args[0]
        params = stmt.compile().params
        assert params["canonical_url"] == "https://example.com/ledger?ref=rss"
        assert params["canonical_url_hash"] == "d" * 64
        assert params["feed_summary"] == "Feed summary"
        assert params["content_hash"] == "a" * 64
        assert params["title_simhash"] == "0123456789abcdef"
        assert params["language"] == "en"
        assert params["ingest_status"] == IngestStatus.NEW.value


class TestInsertLedgerRows:
    def test_inserts_a_batch_and_returns_inserted_count(self):
        session = make_async_session(execute_scalars=[make_uuid(), make_uuid()])
        svc = ArticleService(session)
        source_id = make_uuid()

        inserted = run(
            svc.insert_ledger_rows(
                [
                    {
                        "source_id": source_id,
                        "title": "First",
                        "url": "https://example.com/first",
                        "canonical_url": "https://example.com/first",
                        "canonical_url_hash": "a" * 64,
                        "feed_summary": "First summary",
                        "published_at": None,
                        "language": "en",
                    },
                    {
                        "source_id": source_id,
                        "title": "Second",
                        "url": "https://example.com/second",
                        "canonical_url": "https://example.com/second",
                        "canonical_url_hash": "b" * 64,
                        "feed_summary": None,
                        "published_at": None,
                        "language": "en",
                    },
                ]
            )
        )

        assert inserted == 2
        session.execute.assert_awaited_once()
        stmt = session.execute.call_args.args[0]
        assert "ON CONFLICT DO NOTHING" in str(stmt)

    def test_counts_only_rows_returned_by_postgres(self):
        session = make_async_session(execute_scalars=[make_uuid()])
        svc = ArticleService(session)

        inserted = run(
            svc.insert_ledger_rows(
                [
                    {
                        "source_id": make_uuid(),
                        "title": "Duplicate",
                        "url": "https://example.com/duplicate",
                        "canonical_url": "https://example.com/duplicate",
                        "canonical_url_hash": "c" * 64,
                        "feed_summary": None,
                        "published_at": None,
                        "language": None,
                    }
                ]
            )
        )

        assert inserted == 1

    def test_empty_batch_does_not_query(self):
        session = make_async_session()
        svc = ArticleService(session)

        assert run(svc.insert_ledger_rows([])) == 0
        session.execute.assert_not_awaited()


# ---------------------------------------------------------------------------
# Ledger lookups
# ---------------------------------------------------------------------------


class TestFindArticle:
    def test_find_by_url_returns_article(self):
        mock_article = MagicMock(spec=Article)
        session = make_async_session(execute_scalar_one_or_none=mock_article)
        svc = ArticleService(session)

        assert run(svc.find_by_url("https://example.com/a")) is mock_article

    def test_find_by_url_returns_none(self):
        session = make_async_session(execute_scalar_one_or_none=None)
        svc = ArticleService(session)

        assert run(svc.find_by_url("https://example.com/missing")) is None

    def test_find_by_content_hash_returns_article(self):
        mock_article = MagicMock(spec=Article)
        session = make_async_session(execute_scalar_one_or_none=mock_article)
        svc = ArticleService(session)

        assert run(svc.find_by_content_hash("b" * 64)) is mock_article

    def test_find_by_content_hash_returns_none(self):
        session = make_async_session(execute_scalar_one_or_none=None)
        svc = ArticleService(session)

        assert run(svc.find_by_content_hash("c" * 64)) is None


# ---------------------------------------------------------------------------
# Status and membership writes
# ---------------------------------------------------------------------------


class TestSetIngestStatus:
    def test_returns_updated_row_count(self):
        session = make_async_session()
        session.execute.return_value = _make_cursor_result(2)
        svc = ArticleService(session)

        assert (
            run(svc.set_ingest_status([make_uuid(), make_uuid()], IngestStatus.LABELED))
            == 2
        )

    def test_empty_ids_does_not_query(self):
        session = make_async_session()
        svc = ArticleService(session)

        assert run(svc.set_ingest_status([], IngestStatus.LABELED)) == 0
        session.execute.assert_not_awaited()


class TestAssignEvent:
    def test_returns_updated_row_count(self):
        event_id = make_uuid()
        session = make_async_session()
        session.execute.return_value = _make_cursor_result(3)
        svc = ArticleService(session)

        assert run(svc.assign_event([make_uuid()], event_id)) == 3

        stmt = session.execute.call_args.args[0]
        assert stmt.compile().params["event_id"] == event_id

    def test_empty_ids_does_not_query(self):
        session = make_async_session()
        svc = ArticleService(session)

        assert run(svc.assign_event([], make_uuid())) == 0
        session.execute.assert_not_awaited()

    def test_clear_event_members_returns_row_count(self):
        event_id = make_uuid()
        session = make_async_session()
        session.execute.return_value = _make_cursor_result(4)
        svc = ArticleService(session)

        assert run(svc.clear_event_members(event_id)) == 4

        stmt = session.execute.call_args.args[0]
        assert stmt.compile().params["event_id_1"] == event_id


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


class TestListArticles:
    def test_list_event_articles_returns_members(self):
        articles = [MagicMock(spec=Article), MagicMock(spec=Article)]
        session = make_async_session(execute_scalars=articles)
        svc = ArticleService(session)

        assert run(svc.list_event_articles(make_uuid())) == articles

    def test_list_by_ingest_status_returns_batch(self):
        articles = [MagicMock(spec=Article)]
        session = make_async_session(execute_scalars=articles)
        svc = ArticleService(session)

        result = run(svc.list_by_ingest_status(IngestStatus.NEW, limit=25))

        assert result == articles
        stmt = session.execute.call_args.args[0]
        assert stmt.compile().params["ingest_status_1"] == IngestStatus.NEW.value
        assert stmt.compile().params["param_1"] == 25
