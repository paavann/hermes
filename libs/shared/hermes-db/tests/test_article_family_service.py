"""Tests for hermes_db.services.article_family — ArticleFamilyService."""

from datetime import UTC, datetime
from types import SimpleNamespace

from conftest import make_async_session, make_uuid, run

from hermes_db.models.article_family import ArticleFamily
from hermes_db.services.article_family import ArticleFamilyService


NOW = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


class TestRecentCandidates:
    def test_maps_rows_and_casts_embedding(self):
        family_id = make_uuid()
        representative_id = make_uuid()
        row = SimpleNamespace(
            id=family_id,
            representative_article_id=representative_id,
            title_simhash="0" * 16,
            body_simhash="1" * 16,
            primary_origin_group="example",
            representative_time=NOW,
            embedding=[0.25, 0.5],
        )
        session = make_async_session(execute_all=[row])

        candidates = run(
            ArticleFamilyService(session).recent_candidates(
                since=NOW,
                limit=100,
            )
        )

        assert len(candidates) == 1
        assert candidates[0].family_id == family_id
        assert candidates[0].representative_article_id == representative_id
        assert candidates[0].representative_embedding == (0.25, 0.5)
        assert candidates[0].representative_time == NOW

        sql = str(session.execute.call_args.args[0])
        assert "articles.embedding" in sql
        assert "article_embeddings" not in sql

    def test_missing_embedding_stays_none(self):
        row = SimpleNamespace(
            id=make_uuid(),
            representative_article_id=None,
            title_simhash="0" * 16,
            body_simhash=None,
            primary_origin_group="example",
            representative_time=NOW,
            embedding=None,
        )
        session = make_async_session(execute_all=[row])

        candidates = run(
            ArticleFamilyService(session).recent_candidates(
                since=NOW,
                limit=10,
            )
        )

        assert candidates[0].representative_embedding is None
        assert candidates[0].representative_article_id is None


class TestCreate:
    def test_adds_family_and_assigns_article(self):
        article_id = make_uuid()
        session = make_async_session()

        family_id = run(
            ArticleFamilyService(session).create(
                article_id=article_id,
                title_simhash="a" * 16,
                body_simhash="b" * 16,
                origin_group="example",
            )
        )

        session.add.assert_called_once()
        family = session.add.call_args.args[0]
        assert isinstance(family, ArticleFamily)
        assert family.id == family_id
        assert family.representative_article_id == article_id
        assert family.title_simhash == "a" * 16
        assert family.body_simhash == "b" * 16
        assert family.primary_origin_group == "example"
        assert family.member_count == 1
        session.flush.assert_awaited_once()

        stmt = session.execute.call_args.args[0]
        params = stmt.compile().params
        assert params["family_id"] == family_id


class TestAddMember:
    def test_increments_count_and_assigns_article(self):
        family_id = make_uuid()
        article_id = make_uuid()
        session = make_async_session()

        run(
            ArticleFamilyService(session).add_member(
                family_id=family_id,
                article_id=article_id,
                title_simhash="a" * 16,
                body_simhash=None,
                origin_group="example",
            )
        )

        assert session.execute.await_count == 2
        family_stmt = session.execute.call_args_list[0].args[0]
        family_params = family_stmt.compile().params
        assert family_id in family_params.values()
        assert "representative_article_id" not in family_params

        article_stmt = session.execute.call_args_list[1].args[0]
        article_params = article_stmt.compile().params
        assert article_params["family_id"] == family_id

    def test_can_adopt_earlier_representative(self):
        family_id = make_uuid()
        article_id = make_uuid()
        session = make_async_session()

        run(
            ArticleFamilyService(session).add_member(
                family_id=family_id,
                article_id=article_id,
                title_simhash="a" * 16,
                body_simhash="b" * 16,
                origin_group="example",
                adopt_representative=True,
            )
        )

        family_stmt = session.execute.call_args_list[0].args[0]
        params = family_stmt.compile().params
        assert params["representative_article_id"] == article_id
        assert params["title_simhash"] == "a" * 16
        assert params["body_simhash"] == "b" * 16
        assert params["primary_origin_group"] == "example"


class TestListForArticles:
    def test_empty_input_does_not_query(self):
        session = make_async_session()

        assert run(ArticleFamilyService(session).list_for_articles([])) == []
        session.execute.assert_not_awaited()

    def test_returns_joined_families(self):
        families = [object(), object()]
        session = make_async_session(execute_scalars=families)

        assert run(
            ArticleFamilyService(session).list_for_articles(
                [make_uuid(), make_uuid()]
            )
        ) == families
