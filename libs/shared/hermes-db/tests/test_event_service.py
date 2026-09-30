"""Tests for hermes_db.services.event — EventService.

All tests use mocked AsyncSession instances; no real database is required.
Each method is tested for its happy-path behaviour, edge cases, and any
observable side-effects on the session mock.

Architecture note
-----------------
``EventService`` aggregates ``ArticleService`` internally (composition).
We patch ``ArticleService.create_article`` via ``AsyncMock`` so that event
tests remain isolated from article-creation details.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from conftest import make_async_session, make_event, make_uuid, run
from sqlalchemy.engine import CursorResult

from hermes_db.enums import CredibilityTier, EventStatus
from hermes_db.models.event import Event
from hermes_db.services.event import (
    CREDIBILITY_WEIGHTS,
    EventService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Extraction:
    """Minimal EventExtractionData implementation for tests."""

    def __init__(
        self,
        headline: str = "Test headline",
        summary: str = "Test summary",
        category: str = "Politics",
        category_color: str | None = "#FF0000",
        location_name: str | None = "London, UK",
    ) -> None:
        self.headline = headline
        self.summary = summary
        self.category = category
        self.category_color = category_color
        self.location_name = location_name


class _Geocoding:
    """Minimal GeocodingData implementation for tests."""

    def __init__(self, lat: float = 51.5, lon: float = -0.1) -> None:
        self.latitude = lat
        self.longitude = lon


def _patch_article_create(session: AsyncMock) -> AsyncMock:
    """Patch ArticleService.create_article to be a no-op AsyncMock."""
    mock = AsyncMock(return_value=MagicMock())
    # Attach so EventService internal article_service uses it.
    session._article_create_mock = mock
    return mock


# ---------------------------------------------------------------------------
# CREDIBILITY_WEIGHTS constant
# ---------------------------------------------------------------------------


class TestCredibilityWeights:
    def test_all_tiers_have_weights(self):
        for tier in CredibilityTier:
            assert tier in CREDIBILITY_WEIGHTS

    def test_tier1_is_highest(self):
        assert CREDIBILITY_WEIGHTS[CredibilityTier.TIER_1] > CREDIBILITY_WEIGHTS[CredibilityTier.TIER_2]

    def test_tier4_is_lowest(self):
        assert CREDIBILITY_WEIGHTS[CredibilityTier.TIER_4] < CREDIBILITY_WEIGHTS[CredibilityTier.TIER_3]

    @pytest.mark.parametrize(
        ("tier", "expected"),
        [
            (CredibilityTier.TIER_1, 3.0),
            (CredibilityTier.TIER_2, 2.0),
            (CredibilityTier.TIER_3, 1.0),
            (CredibilityTier.TIER_4, 0.5),
        ],
    )
    def test_exact_weights(self, tier, expected):
        assert CREDIBILITY_WEIGHTS[tier] == expected


# ---------------------------------------------------------------------------
# create_event_with_article
# ---------------------------------------------------------------------------


class TestCreateEventWithArticle:
    def _make_session_and_svc(self):
        session = make_async_session()
        # Ensure flush is awaitable and sets event.id after it runs.
        async def _flush():
            pass
        session.flush = AsyncMock(side_effect=_flush)
        svc = EventService(session)
        return session, svc

    def _run_create(
        self,
        svc: EventService,
        *,
        geocoding=None,
        credibility: CredibilityTier = CredibilityTier.TIER_1,
        embedding: list[float] | None = None,
    ) -> Event:
        extraction = _Extraction()
        return run(
            svc.create_event_with_article(
                extraction=extraction,
                geocoding=geocoding,
                article_title="Article title",
                article_url="https://example.com/article",
                source_id=make_uuid(),
                source_credibility=credibility,
                embedding=embedding,
            )
        )

    def test_returns_event_instance(self):
        """Must return an Event ORM object."""
        session, svc = self._make_session_and_svc()
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            result = self._run_create(svc)
        assert isinstance(result, Event)

    def test_event_added_to_session(self):
        """session.add must be called with the new Event."""
        session, svc = self._make_session_and_svc()
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            result = self._run_create(svc)
        session.add.assert_called()
        call_args = [args[0] for args, _ in session.add.call_args_list]
        assert result in call_args

    def test_session_flushed_before_article_creation(self):
        """flush() must be awaited so that event.id is available for the article FK."""
        session, svc = self._make_session_and_svc()
        flush_called_before_article = []

        async def _create_article(**kwargs):
            flush_called_before_article.append(session.flush.await_count)
            return MagicMock()

        with patch.object(svc._article_service, "create_article", side_effect=_create_article):
            self._run_create(svc)

        # flush must have been awaited at least once before article creation.
        assert flush_called_before_article and flush_called_before_article[0] >= 1

    def test_session_committed(self):
        """commit() must be awaited at the end."""
        session, svc = self._make_session_and_svc()
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            self._run_create(svc)
        session.commit.assert_awaited_once()

    def test_initial_score_from_credibility(self):
        """trending_score must equal the credibility weight of the source."""
        session, svc = self._make_session_and_svc()
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            event = self._run_create(svc, credibility=CredibilityTier.TIER_2)
        assert event.trending_score == CREDIBILITY_WEIGHTS[CredibilityTier.TIER_2]

    def test_article_count_initialised_to_one(self):
        session, svc = self._make_session_and_svc()
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            event = self._run_create(svc)
        assert event.article_count == 1

    def test_location_wkt_set_when_geocoding_provided(self):
        session, svc = self._make_session_and_svc()
        geo = _Geocoding(lat=48.85, lon=2.35)  # Paris
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            event = self._run_create(svc, geocoding=geo)
        assert event.location is not None
        assert "POINT" in event.location
        assert "2.35" in event.location
        assert "48.85" in event.location

    def test_location_none_when_no_geocoding(self):
        session, svc = self._make_session_and_svc()
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            event = self._run_create(svc, geocoding=None)
        assert event.location is None

    def test_embedding_stored_on_event(self):
        session, svc = self._make_session_and_svc()
        emb = [0.1] * 2048
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            event = self._run_create(svc, embedding=emb)
        assert event.embedding == emb

    def test_embedding_none_when_not_provided(self):
        session, svc = self._make_session_and_svc()
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            event = self._run_create(svc, embedding=None)
        assert event.embedding is None

    def test_headline_and_summary_set(self):
        session, svc = self._make_session_and_svc()
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            event = self._run_create(svc)
        assert event.ai_headline == "Test headline"
        assert event.ai_summary == "Test summary"

    @pytest.mark.parametrize("credibility", list(CredibilityTier))
    def test_all_credibility_tiers_produce_correct_initial_score(self, credibility):
        session, svc = self._make_session_and_svc()
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            event = self._run_create(svc, credibility=credibility)
        assert event.trending_score == CREDIBILITY_WEIGHTS[credibility]


# ---------------------------------------------------------------------------
# add_article_to_event
# ---------------------------------------------------------------------------


class TestAddArticleToEvent:
    def _make_session_and_svc(self, event: MagicMock | None = None):
        session = make_async_session(get_return=event)
        svc = EventService(session)
        return session, svc

    def test_returns_none_when_event_not_found(self):
        """When the event doesn't exist, the method must return None gracefully."""
        session, svc = self._make_session_and_svc(event=None)
        result = run(
            svc.add_article_to_event(
                event_id=make_uuid(),
                article_title="T",
                article_url="https://example.com/x",
                source_id=make_uuid(),
                source_credibility=CredibilityTier.TIER_3,
            )
        )
        assert result is None

    def test_returns_updated_event(self):
        """When event is found, the updated Event must be returned."""
        event = make_event(status=EventStatus.ACTIVE, trending_score=3.0, article_count=1)
        session, svc = self._make_session_and_svc(event=event)
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            result = run(
                svc.add_article_to_event(
                    event_id=event.id,
                    article_title="New article",
                    article_url="https://example.com/new",
                    source_id=make_uuid(),
                    source_credibility=CredibilityTier.TIER_2,
                )
            )
        assert result is event

    def test_article_count_incremented(self):
        event = make_event(article_count=3)
        session, svc = self._make_session_and_svc(event=event)
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            run(
                svc.add_article_to_event(
                    event_id=event.id,
                    article_title="T",
                    article_url="https://example.com/t",
                    source_id=make_uuid(),
                    source_credibility=CredibilityTier.TIER_3,
                )
            )
        assert event.article_count == 4

    def test_trending_score_incremented_by_credibility_weight(self):
        event = make_event(trending_score=2.0)
        session, svc = self._make_session_and_svc(event=event)
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            run(
                svc.add_article_to_event(
                    event_id=event.id,
                    article_title="T",
                    article_url="https://example.com/t2",
                    source_id=make_uuid(),
                    source_credibility=CredibilityTier.TIER_1,
                )
            )
        assert event.trending_score == pytest.approx(2.0 + CREDIBILITY_WEIGHTS[CredibilityTier.TIER_1])

    def test_stale_event_reactivated(self):
        """Adding an article to a STALE event must flip it back to ACTIVE."""
        event = make_event(status=EventStatus.STALE)
        session, svc = self._make_session_and_svc(event=event)
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            run(
                svc.add_article_to_event(
                    event_id=event.id,
                    article_title="T",
                    article_url="https://example.com/stale",
                    source_id=make_uuid(),
                    source_credibility=CredibilityTier.TIER_3,
                )
            )
        assert event.status == EventStatus.ACTIVE

    def test_active_event_stays_active(self):
        event = make_event(status=EventStatus.ACTIVE)
        session, svc = self._make_session_and_svc(event=event)
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            run(
                svc.add_article_to_event(
                    event_id=event.id,
                    article_title="T",
                    article_url="https://example.com/act",
                    source_id=make_uuid(),
                    source_credibility=CredibilityTier.TIER_2,
                )
            )
        assert event.status == EventStatus.ACTIVE

    def test_commit_called(self):
        event = make_event()
        session, svc = self._make_session_and_svc(event=event)
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            run(
                svc.add_article_to_event(
                    event_id=event.id,
                    article_title="T",
                    article_url="https://example.com/commit",
                    source_id=make_uuid(),
                    source_credibility=CredibilityTier.TIER_3,
                )
            )
        session.commit.assert_awaited_once()

    def test_no_commit_when_event_not_found(self):
        """commit must NOT be called if the event doesn't exist."""
        session, svc = self._make_session_and_svc(event=None)
        run(
            svc.add_article_to_event(
                event_id=make_uuid(),
                article_title="T",
                article_url="https://example.com/nc",
                source_id=make_uuid(),
                source_credibility=CredibilityTier.TIER_3,
            )
        )
        session.commit.assert_not_awaited()

    @pytest.mark.parametrize("credibility", list(CredibilityTier))
    def test_score_increment_per_tier(self, credibility):
        initial = 1.0
        event = make_event(trending_score=initial)
        session, svc = self._make_session_and_svc(event=event)
        with patch.object(svc._article_service, "create_article", new_callable=AsyncMock):
            run(
                svc.add_article_to_event(
                    event_id=event.id,
                    article_title="T",
                    article_url=f"https://example.com/{credibility}",
                    source_id=make_uuid(),
                    source_credibility=credibility,
                )
            )
        assert event.trending_score == pytest.approx(initial + CREDIBILITY_WEIGHTS[credibility])


# ---------------------------------------------------------------------------
# get_active_events
# ---------------------------------------------------------------------------


class TestGetActiveEvents:
    def test_returns_list_of_dicts(self):
        """Result must be a list of dictionaries."""
        session = make_async_session(execute_all=[])
        svc = EventService(session)
        result = run(svc.get_active_events())
        assert isinstance(result, list)

    def test_empty_db_returns_empty_list(self):
        session = make_async_session(execute_all=[])
        svc = EventService(session)
        assert run(svc.get_active_events()) == []

    def test_rows_converted_to_dicts(self):
        """Each DB row must be converted to a dict with the right keys."""
        event_id = make_uuid()
        session = make_async_session(
            execute_all=[(event_id, "Big headline", "Berlin, DE", "Economy")]
        )
        svc = EventService(session)
        result = run(svc.get_active_events())
        assert len(result) == 1
        row = result[0]
        assert row["id"] == str(event_id)
        assert row["headline"] == "Big headline"
        assert row["location_name"] == "Berlin, DE"
        assert row["category"] == "Economy"

    def test_null_location_name_becomes_na(self):
        """location_name=None in the DB must become 'N/A' in the output."""
        event_id = make_uuid()
        session = make_async_session(
            execute_all=[(event_id, "Headline", None, "Tech")]
        )
        svc = EventService(session)
        result = run(svc.get_active_events())
        assert result[0]["location_name"] == "N/A"

    def test_multiple_rows_all_returned(self):
        rows = [
            (make_uuid(), f"Event {i}", f"City {i}", "Category")
            for i in range(5)
        ]
        session = make_async_session(execute_all=rows)
        svc = EventService(session)
        result = run(svc.get_active_events())
        assert len(result) == 5

    def test_id_is_stringified_uuid(self):
        """Event IDs must be converted from UUID to str."""
        event_id = make_uuid()
        session = make_async_session(
            execute_all=[(event_id, "H", "L", "C")]
        )
        svc = EventService(session)
        result = run(svc.get_active_events())
        assert isinstance(result[0]["id"], str)
        assert result[0]["id"] == str(event_id)


# ---------------------------------------------------------------------------
# get_active_events_by_embeddings
# ---------------------------------------------------------------------------


class TestGetActiveEventsByEmbeddings:
    def test_empty_embeddings_list_returns_empty(self):
        session = make_async_session()
        svc = EventService(session)
        result = run(svc.get_active_events_by_embeddings([]))
        assert result == []
        session.execute.assert_not_awaited()

    def test_none_embedding_in_list_skipped(self):
        """An empty embedding vector inside the list must be skipped."""
        session = make_async_session(execute_all=[])
        svc = EventService(session)
        result = run(svc.get_active_events_by_embeddings([[], []]))
        assert result == []

    def test_returns_unique_events(self):
        """The same event returned from multiple embedding queries must appear once."""
        event_id = make_uuid()
        row = (event_id, "Headline", "City", "Cat")
        session = make_async_session(execute_all=[row])
        svc = EventService(session)
        embeddings = [[0.1] * 2048, [0.2] * 2048]
        result = run(svc.get_active_events_by_embeddings(embeddings))
        assert len(result) == 1
        assert result[0]["id"] == str(event_id)

    def test_result_contains_expected_keys(self):
        event_id = make_uuid()
        session = make_async_session(
            execute_all=[(event_id, "H", "L", "C")]
        )
        svc = EventService(session)
        result = run(svc.get_active_events_by_embeddings([[0.1] * 2048]))
        assert set(result[0].keys()) == {"id", "headline", "location_name", "category"}

    def test_null_location_name_becomes_na(self):
        event_id = make_uuid()
        session = make_async_session(
            execute_all=[(event_id, "H", None, "C")]
        )
        svc = EventService(session)
        result = run(svc.get_active_events_by_embeddings([[0.1] * 2048]))
        assert result[0]["location_name"] == "N/A"

    def test_execute_called_per_non_empty_embedding(self):
        """The DB must be queried once per non-empty embedding vector."""
        session = make_async_session(execute_all=[])
        svc = EventService(session)
        embeddings = [[0.1] * 2048, [0.2] * 2048, [0.3] * 2048]
        run(svc.get_active_events_by_embeddings(embeddings))
        assert session.execute.await_count == 3


# ---------------------------------------------------------------------------
# article_url_exists (delegation)
# ---------------------------------------------------------------------------


class TestArticleUrlExistsDelegation:
    def test_delegates_to_article_service(self):
        """EventService.article_url_exists must delegate to ArticleService."""
        session = make_async_session(execute_scalar_one_or_none=make_uuid())
        svc = EventService(session)
        result = run(svc.article_url_exists("https://example.com/existing"))
        assert result is True

    def test_returns_false_when_url_not_found(self):
        session = make_async_session(execute_scalar_one_or_none=None)
        svc = EventService(session)
        result = run(svc.article_url_exists("https://example.com/new"))
        assert result is False


# ---------------------------------------------------------------------------
# _transition_event_status (internal helper)
# ---------------------------------------------------------------------------


class TestTransitionEventStatus:
    def _make_cursor_result(self, rowcount: int) -> MagicMock:
        """Produce a CursorResult mock with the given rowcount."""
        cursor = MagicMock(spec=CursorResult)
        cursor.rowcount = rowcount
        return cursor

    def test_returns_rowcount_from_cursor_result(self):
        """When the DB returns a CursorResult, rowcount must be returned."""
        cursor = self._make_cursor_result(5)
        session = make_async_session()
        session.execute = AsyncMock(return_value=cursor)
        svc = EventService(session)
        now = datetime.now(UTC).replace(tzinfo=None)
        count = run(
            svc._transition_event_status(
                from_status=EventStatus.ACTIVE,
                to_status=EventStatus.STALE,
                cutoff=now,
            )
        )
        assert count == 5

    def test_returns_zero_when_not_cursor_result(self):
        """If execute returns a non-CursorResult (edge case), return 0 safely."""
        non_cursor = MagicMock()  # Not a CursorResult spec
        session = make_async_session()
        session.execute = AsyncMock(return_value=non_cursor)
        svc = EventService(session)
        now = datetime.now(UTC).replace(tzinfo=None)
        count = run(
            svc._transition_event_status(
                from_status=EventStatus.STALE,
                to_status=EventStatus.ARCHIVED,
                cutoff=now,
            )
        )
        assert count == 0


# ---------------------------------------------------------------------------
# run_lifecycle_transitions
# ---------------------------------------------------------------------------


class TestRunLifecycleTransitions:
    def _make_svc_with_rowcounts(
        self, stale_count: int = 2, archived_count: int = 1
    ) -> tuple[EventService, AsyncMock]:
        """Build EventService where each execute call returns increasing rowcounts."""
        session = make_async_session()

        # execute is called 3 times: decay UPDATE, stale UPDATE, archive UPDATE.
        # We simulate rowcounts via side_effect on execute.
        call_index = {"n": 0}
        counts = [0, stale_count, archived_count]  # decay returns 0, others vary

        async def _execute(stmt):
            idx = call_index["n"]
            call_index["n"] += 1
            cursor = MagicMock(spec=CursorResult)
            cursor.rowcount = counts[idx] if idx < len(counts) else 0
            return cursor

        session.execute = AsyncMock(side_effect=_execute)
        svc = EventService(session)
        return svc, session

    def test_returns_dict_with_staled_and_archived_keys(self):
        svc, _ = self._make_svc_with_rowcounts()
        result = run(svc.run_lifecycle_transitions())
        assert "staled" in result
        assert "archived" in result

    def test_staled_count_reflects_db_result(self):
        svc, _ = self._make_svc_with_rowcounts(stale_count=3, archived_count=0)
        result = run(svc.run_lifecycle_transitions())
        assert result["staled"] == 3

    def test_archived_count_reflects_db_result(self):
        svc, _ = self._make_svc_with_rowcounts(stale_count=0, archived_count=7)
        result = run(svc.run_lifecycle_transitions())
        assert result["archived"] == 7

    def test_commit_called_once(self):
        svc, session = self._make_svc_with_rowcounts()
        run(svc.run_lifecycle_transitions())
        session.commit.assert_awaited_once()

    def test_three_db_statements_executed(self):
        """Must execute decay + stale transition + archive transition = 3 calls."""
        svc, session = self._make_svc_with_rowcounts()
        run(svc.run_lifecycle_transitions())
        assert session.execute.await_count == 3

    def test_zero_transitions_when_no_events(self):
        svc, _ = self._make_svc_with_rowcounts(stale_count=0, archived_count=0)
        result = run(svc.run_lifecycle_transitions())
        assert result == {"staled": 0, "archived": 0}
