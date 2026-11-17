"""Tests for hermes_db.services.article_label — ArticleLabelService.

All tests use a mocked AsyncSession so no database is involved.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from conftest import make_async_session, make_uuid, run

from hermes_db.enums import ArticleType, EventScope
from hermes_db.models.article_label import ArticleLabel
from hermes_db.services.article_label import ArticleLabelService


class _Label:
    """Minimal ArticleLabelData implementation for tests."""

    def __init__(self) -> None:
        self.is_event = True
        self.article_type = ArticleType.BREAKING
        self.event_time = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
        self.severity = 4
        self.scope = EventScope.COUNTRY
        self.confidence = 0.91
        self.fact = "A magnitude 6.1 earthquake struck the coast."
        self.scale_facts = {"magnitude": 6.1}
        self.entities = [{"name": "Example City", "type": "location"}]
        self.locations = [{"name": "Example City", "country_code": "EX"}]


class TestUpsertLabel:
    def test_returns_label_from_returning_clause(self):
        stored = MagicMock(spec=ArticleLabel)
        session = make_async_session(execute_scalar_one_or_none=stored)
        svc = ArticleLabelService(session)

        result = run(
            svc.upsert_label(
                article_id=make_uuid(),
                prompt_version="label-v1",
                model="test/model",
                label=_Label(),
            )
        )

        assert result is stored
        session.execute.assert_awaited_once()
        session.add.assert_not_called()

    def test_values_include_label_payload(self):
        session = make_async_session(execute_scalar_one_or_none=MagicMock())
        svc = ArticleLabelService(session)
        article_id = make_uuid()

        run(
            svc.upsert_label(
                article_id=article_id,
                prompt_version="label-v1",
                model="test/model",
                label=_Label(),
            )
        )

        stmt = session.execute.call_args.args[0]
        params = stmt.compile().params
        assert params["article_id"] == article_id
        assert params["prompt_version"] == "label-v1"
        assert params["model"] == "test/model"
        assert params["is_event"] is True
        assert params["severity"] == 4
        assert params["fact"] == "A magnitude 6.1 earthquake struck the coast."
        assert params["scale_facts"] == {"magnitude": 6.1}


class TestReadLabels:
    def test_get_label_returns_match(self):
        stored = MagicMock(spec=ArticleLabel)
        session = make_async_session(execute_scalar_one_or_none=stored)
        svc = ArticleLabelService(session)

        assert run(svc.get_label(make_uuid(), "label-v1")) is stored

    def test_get_label_returns_none_when_missing(self):
        session = make_async_session(execute_scalar_one_or_none=None)
        svc = ArticleLabelService(session)

        assert run(svc.get_label(make_uuid(), "label-v1")) is None

    def test_has_label_true(self):
        session = make_async_session(execute_scalar_one_or_none=make_uuid())
        svc = ArticleLabelService(session)

        assert run(svc.has_label(make_uuid(), "label-v1")) is True

    def test_has_label_false(self):
        session = make_async_session(execute_scalar_one_or_none=None)
        svc = ArticleLabelService(session)

        assert run(svc.has_label(make_uuid(), "label-v1")) is False

    def test_list_labels_returns_batch(self):
        labels = [MagicMock(spec=ArticleLabel), MagicMock(spec=ArticleLabel)]
        session = make_async_session(execute_scalars=labels)
        svc = ArticleLabelService(session)

        result = run(svc.list_labels([make_uuid(), make_uuid()], "label-v1"))

        assert result == labels
        session.execute.assert_awaited_once()

    def test_list_labels_empty_input_does_not_query(self):
        session = make_async_session()
        svc = ArticleLabelService(session)

        assert run(svc.list_labels([], "label-v1")) == []
        session.execute.assert_not_awaited()
