"""Tests for hermes_db.services.article — ArticleService.

All tests use a mocked AsyncSession so no database is involved.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

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
    def _make_svc(self) -> tuple[ArticleService, AsyncMock]:
        session = make_async_session()
        return ArticleService(session), session

    def test_returns_article_instance(self):
        """create_article must return an Article ORM object."""
        svc, _ = self._make_svc()
        result = run(
            svc.create_article(
                event_id=make_uuid(),
                source_id=make_uuid(),
                title="Test title",
                url="https://example.com/article-1",
            )
        )
        assert isinstance(result, Article)

    def test_article_fields_populated(self):
        """Returned article must carry the supplied field values."""
        svc, _ = self._make_svc()
        event_id = make_uuid()
        source_id = make_uuid()
        published = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)

        article = run(
            svc.create_article(
                event_id=event_id,
                source_id=source_id,
                title="Breaking news",
                url="https://example.com/breaking",
                published_at=published,
            )
        )
        assert article.event_id == event_id
        assert article.source_id == source_id
        assert article.title == "Breaking news"
        assert article.url == "https://example.com/breaking"
        assert article.published_at == published

    def test_article_added_to_session(self):
        """session.add must be called with the new Article object."""
        svc, session = self._make_svc()
        article = run(
            svc.create_article(
                event_id=make_uuid(),
                source_id=make_uuid(),
                title="Title",
                url="https://example.com/x",
            )
        )
        session.add.assert_called_once_with(article)

    def test_commit_not_called(self):
        """create_article must NOT commit — that's the caller's responsibility."""
        svc, session = self._make_svc()
        run(
            svc.create_article(
                event_id=make_uuid(),
                source_id=make_uuid(),
                title="T",
                url="https://example.com/y",
            )
        )
        session.commit.assert_not_awaited()

    def test_published_at_defaults_to_none(self):
        """When published_at is omitted it should default to None."""
        svc, _ = self._make_svc()
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
