"""Tests for hermes_db.services.article — ArticleService.

All tests use a mocked AsyncSession so no database is involved.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from conftest import make_async_session, make_uuid, run

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

