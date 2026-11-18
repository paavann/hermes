"""Tests for the source sync service.

These tests mock the database layer and file system to validate
the upsert/disable logic in isolation.
"""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from hermes_db.enums import (
    SourceFeedProvider,
    SourceFetchPolicy,
    SourceType,
)
from hermes_db.models import Source
from hermes_db.services.source import (
    DueSource,
    SourceService,
    canonical_domain_from_url,
    load_sources_config,
    sync_sources_from_config,
)


# --- Helpers ---


def _make_source(
    slug: str,
    name: str = "Test",
    url: str = "https://example.com",
    feed_url: str | None = "https://example.com/rss",
    fallback_feed_url: str | None = None,
    feed_provider: SourceFeedProvider = SourceFeedProvider.PUBLISHER,
    canonical_domain: str | None = "example.com",
    paywall: bool = False,
    fetch_policy: SourceFetchPolicy = SourceFetchPolicy.FULL_TEXT,
    credibility: str = "TIER_3",
    source_type: SourceType = SourceType.RSS,
    is_active: bool = True,
    origin_group: str | None = None,
    country_code: str | None = None,
    language: str | None = None,
    consecutive_failures: int = 0,
) -> MagicMock:
    """Create a mock Source ORM object."""
    source = MagicMock(spec=Source)
    source.slug = slug
    source.name = name
    source.url = url
    source.feed_url = feed_url
    source.fallback_feed_url = fallback_feed_url
    source.feed_provider = feed_provider
    source.canonical_domain = canonical_domain
    source.paywall = paywall
    source.fetch_policy = fetch_policy
    source.credibility = credibility
    source.source_type = source_type
    source.is_active = is_active
    source.origin_group = origin_group
    source.country_code = country_code
    source.language = language
    source.consecutive_failures = consecutive_failures
    return source


def _mock_session(
    existing_sources: list | None = None,
) -> AsyncMock:
    """Create a mock AsyncSession.

    The mock tracks which sources exist by slug. It uses a simple
    counter to distinguish between "select by slug" calls (which
    return scalar_one_or_none) and "select all" calls (which return
    scalars().all()).
    """
    session = AsyncMock()

    if existing_sources is None:
        existing_sources = []

    source_by_slug = {s.slug: s for s in existing_sources}
    call_counter = {"n": 0}

    async def mock_execute(stmt):
        result = MagicMock()
        call_counter["n"] += 1

        # The sync function calls execute() N times for slug lookups
        # (one per config entry), then once for "select all".
        # We detect the "select all" call by checking if the call
        # index is beyond the number of per-entry lookups.
        # For a simpler approach: scalar_one_or_none is called for
        # slug lookups, scalars().all() for the "select all" query.
        result.scalar_one_or_none = MagicMock(return_value=None)
        result.scalars = MagicMock()
        result.scalars.return_value.all = MagicMock(
            return_value=existing_sources,
        )

        # Try to find a matching source by slug. We inspect the
        # compiled statement to find which slug is being queried.
        for slug, src in source_by_slug.items():
            try:
                compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
                if slug in compiled:
                    result.scalar_one_or_none = MagicMock(return_value=src)
                    break
            except Exception:
                pass

        return result

    session.execute = mock_execute
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


# --- Tests for load_sources_config ---


def test_load_sources_config_valid():
    """Should parse a valid JSON array from the config file."""
    sample = [{"slug": "bbc-world", "name": "BBC World"}]

    with patch.object(Path, "read_text", return_value=json.dumps(sample)):
        result = asyncio.run(load_sources_config())
        assert result == sample


def test_load_sources_config_not_a_list():
    """Should raise ValueError if the JSON is not an array."""
    import pytest

    with (
        patch.object(Path, "read_text", return_value='{"slug": "bbc"}'),
        pytest.raises(ValueError, match="JSON array"),
    ):
        asyncio.run(load_sources_config())


def test_load_sources_config_file_not_found():
    """Should raise FileNotFoundError if the file is missing."""
    import pytest

    with (
        patch.object(Path, "read_text", side_effect=FileNotFoundError),
        pytest.raises(FileNotFoundError),
    ):
        asyncio.run(load_sources_config())


# --- Tests for sync_sources_from_config ---


def test_sync_inserts_new_sources():
    """New sources from the config should be inserted into the DB."""
    config = [
        {
            "slug": "reuters-world",
            "name": "Reuters World",
            "url": "https://reuters.com",
            "feed_url": "https://reuters.com/rss/world",
            "credibility": "TIER_1",
            "origin_group": "reuters",
            "country_code": "GB",
            "language": "en",
        }
    ]
    session = _mock_session(existing_sources=[])

    with patch(
        "hermes_db.services.source.load_sources_config",
        new_callable=AsyncMock,
        return_value=config,
    ):
        stats = asyncio.run(sync_sources_from_config(session))

    assert stats["inserted"] == 1
    assert stats["updated"] == 0
    assert stats["disabled"] == 0
    session.add.assert_called_once()

    inserted = session.add.call_args.args[0]
    assert inserted.origin_group == "reuters"
    assert inserted.country_code == "GB"
    assert inserted.language == "en"
    assert inserted.feed_provider == SourceFeedProvider.PUBLISHER
    assert inserted.fetch_policy == SourceFetchPolicy.FULL_TEXT
    assert inserted.paywall is False
    assert inserted.canonical_domain == "reuters.com"


def test_sync_persists_feed_metadata():
    """Feed provider, fallback, paywall, and policy are config-owned."""
    config = [
        {
            "slug": "nyt-world",
            "name": "The New York Times",
            "url": "https://www.nytimes.com/section/world",
            "feed_url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
            "fallback_feed_url": "https://news.google.com/rss/search?q=source:NYT",
            "feed_provider": "PUBLISHER",
            "paywall": True,
            "fetch_policy": "SUMMARY_ONLY",
        }
    ]
    session = _mock_session(existing_sources=[])

    with patch(
        "hermes_db.services.source.load_sources_config",
        new_callable=AsyncMock,
        return_value=config,
    ):
        asyncio.run(sync_sources_from_config(session))

    inserted = session.add.call_args.args[0]
    assert (
        inserted.fallback_feed_url == "https://news.google.com/rss/search?q=source:NYT"
    )
    assert inserted.feed_provider == SourceFeedProvider.PUBLISHER
    assert inserted.paywall is True
    assert inserted.fetch_policy == SourceFetchPolicy.SUMMARY_ONLY
    assert inserted.canonical_domain == "nytimes.com"


def test_sync_clears_removed_feed_metadata():
    """A removed fallback must not survive the next config sync."""
    existing = _make_source(
        "wsj-world",
        fallback_feed_url="https://old.example.com/feed",
        paywall=True,
        fetch_policy=SourceFetchPolicy.SUMMARY_ONLY,
    )
    config = [
        {
            "slug": "wsj-world",
            "name": "WSJ World",
            "url": "https://example.com",
            "feed_url": "https://example.com/rss",
            "feed_provider": "PUBLISHER",
            "paywall": False,
            "fetch_policy": "FULL_TEXT",
        }
    ]
    session = _mock_session(existing_sources=[existing])

    with patch(
        "hermes_db.services.source.load_sources_config",
        new_callable=AsyncMock,
        return_value=config,
    ):
        stats = asyncio.run(sync_sources_from_config(session))

    assert stats["updated"] == 1
    assert existing.fallback_feed_url is None
    assert existing.paywall is False
    assert existing.fetch_policy == SourceFetchPolicy.FULL_TEXT


def test_sync_does_not_commit():
    """The ingest stage owns the transaction boundary for source sync."""
    config = [
        {
            "slug": "bbc-world",
            "name": "BBC World",
            "url": "https://bbc.com",
            "feed_url": "https://bbc.com/rss",
        }
    ]
    session = _mock_session(existing_sources=[])

    with patch(
        "hermes_db.services.source.load_sources_config",
        new_callable=AsyncMock,
        return_value=config,
    ):
        asyncio.run(sync_sources_from_config(session))

    session.commit.assert_not_awaited()


def test_canonical_domain_strips_www_and_port():
    assert (
        canonical_domain_from_url("https://www.example.com:8443/world") == "example.com"
    )
    assert canonical_domain_from_url("not a url") is None
    assert canonical_domain_from_url(None) is None


def test_sync_normalizes_source_metadata():
    """Config metadata must be stored in a comparable canonical form."""
    config = [
        {
            "slug": "bbc-world",
            "name": "BBC World",
            "url": "https://bbc.com",
            "feed_url": "https://bbc.com/rss",
            "origin_group": " BBC ",
            "country_code": " gb ",
            "language": " EN ",
        }
    ]
    session = _mock_session(existing_sources=[])

    with patch(
        "hermes_db.services.source.load_sources_config",
        new_callable=AsyncMock,
        return_value=config,
    ):
        asyncio.run(sync_sources_from_config(session))

    inserted = session.add.call_args.args[0]
    assert inserted.origin_group == "bbc"
    assert inserted.country_code == "GB"
    assert inserted.language == "en"


def test_sync_updates_source_metadata():
    """Changing independence metadata in the config must update the row."""
    existing = _make_source(
        "bbc-world",
        origin_group=None,
        country_code=None,
        language=None,
    )
    config = [
        {
            "slug": "bbc-world",
            "name": "Test",
            "url": "https://example.com",
            "feed_url": "https://example.com/rss",
            "origin_group": "bbc",
            "country_code": "GB",
            "language": "en",
        }
    ]
    session = _mock_session(existing_sources=[existing])

    with patch(
        "hermes_db.services.source.load_sources_config",
        new_callable=AsyncMock,
        return_value=config,
    ):
        stats = asyncio.run(sync_sources_from_config(session))

    assert stats["updated"] == 1
    assert existing.origin_group == "bbc"
    assert existing.country_code == "GB"
    assert existing.language == "en"


def test_sync_skips_entries_without_slug():
    """Entries missing a slug should be skipped with a warning."""
    config = [{"name": "No Slug Source", "url": "https://example.com"}]
    session = _mock_session(existing_sources=[])

    with patch(
        "hermes_db.services.source.load_sources_config",
        new_callable=AsyncMock,
        return_value=config,
    ):
        stats = asyncio.run(sync_sources_from_config(session))

    assert stats["inserted"] == 0
    session.add.assert_not_called()


def test_sync_disables_removed_sources():
    """DB sources not in the config should be soft-disabled."""
    existing = _make_source("old-source", is_active=True)
    config = [
        {
            "slug": "new-source",
            "name": "New Source",
            "url": "https://new.com",
            "feed_url": "https://new.com/rss",
            "credibility": "TIER_2",
        }
    ]
    session = _mock_session(existing_sources=[existing])

    with patch(
        "hermes_db.services.source.load_sources_config",
        new_callable=AsyncMock,
        return_value=config,
    ):
        stats = asyncio.run(sync_sources_from_config(session))

    assert stats["disabled"] == 1
    assert existing.is_active is False


def test_sync_handles_missing_config_file():
    """Should return zero stats and not crash when the config file is missing."""
    session = _mock_session()

    with patch(
        "hermes_db.services.source.load_sources_config",
        new_callable=AsyncMock,
        side_effect=FileNotFoundError("not found"),
    ):
        stats = asyncio.run(sync_sources_from_config(session))

    assert stats["inserted"] == 0
    assert stats["updated"] == 0
    assert stats["disabled"] == 0


def test_sync_handles_invalid_json():
    """Should return zero stats and not crash on malformed JSON."""
    session = _mock_session()

    with patch(
        "hermes_db.services.source.load_sources_config",
        new_callable=AsyncMock,
        side_effect=json.JSONDecodeError("bad", "", 0),
    ):
        stats = asyncio.run(sync_sources_from_config(session))

    assert stats["inserted"] == 0


def test_sync_is_idempotent():
    """Running sync twice with the same config should not insert duplicates."""
    config = [
        {
            "slug": "bbc-world",
            "name": "BBC World",
            "url": "https://bbc.com",
            "feed_url": "https://feeds.bbci.co.uk/news/world/rss.xml",
            "credibility": "TIER_1",
        }
    ]
    existing = _make_source(
        slug="bbc-world",
        name="BBC World",
        url="https://bbc.com",
        feed_url="https://feeds.bbci.co.uk/news/world/rss.xml",
        credibility="TIER_1",
        is_active=True,
        canonical_domain="bbc.com",
    )
    session = _mock_session(existing_sources=[existing])

    with patch(
        "hermes_db.services.source.load_sources_config",
        new_callable=AsyncMock,
        return_value=config,
    ):
        stats = asyncio.run(sync_sources_from_config(session))

    # Nothing should change — already in sync.
    assert stats["inserted"] == 0
    assert stats["disabled"] == 0
    session.add.assert_not_called()


def test_sync_updates_changed_source_fields():
    """When a source's URL or credibility changes in the config, it must be updated."""
    existing = _make_source(
        slug="bbc-world",
        name="BBC World",
        url="https://old-bbc.com",  # will be overwritten
        credibility="TIER_3",  # will be upgraded to TIER_1
        is_active=True,
    )
    config = [
        {
            "slug": "bbc-world",
            "name": "BBC World",
            "url": "https://new-bbc.com",
            "feed_url": "https://feeds.bbci.co.uk/news/world/rss.xml",
            "credibility": "TIER_1",
        }
    ]
    session = _mock_session(existing_sources=[existing])

    with patch(
        "hermes_db.services.source.load_sources_config",
        new_callable=AsyncMock,
        return_value=config,
    ):
        stats = asyncio.run(sync_sources_from_config(session))

    assert stats["updated"] == 1
    assert existing.url == "https://new-bbc.com"
    assert existing.credibility == "TIER_1"


def test_sync_reactivates_inactive_source():
    """A source that was disabled but appears in the config must be reactivated."""
    existing = _make_source(slug="guardian-world", is_active=False)
    config = [
        {
            "slug": "guardian-world",
            "name": "The Guardian",
            "url": "https://guardian.com",
            "feed_url": "https://guardian.com/rss",
            "credibility": "TIER_3",
        }
    ]
    session = _mock_session(existing_sources=[existing])

    with patch(
        "hermes_db.services.source.load_sources_config",
        new_callable=AsyncMock,
        return_value=config,
    ):
        stats = asyncio.run(sync_sources_from_config(session))

    assert stats["updated"] == 1
    assert existing.is_active is True


# --- Tests for SourceService ---


def test_source_service_get_due_sources():
    """Should return sources that are due for fetching."""
    now = datetime.now(UTC)
    source_id1 = uuid.uuid4()
    source_id2 = uuid.uuid4()
    source_id3 = uuid.uuid4()

    # Source 1: never fetched -> should be due
    s1 = _make_source("s1", name="S1", feed_url="https://s1.com/rss")
    s1.id = source_id1
    s1.fetch_interval_minutes = 15
    s1.last_fetched_at = None

    # Source 2: fetched 5 mins ago (interval 15) -> not due
    s2 = _make_source("s2", name="S2", feed_url="https://s2.com/rss")
    s2.id = source_id2
    s2.fetch_interval_minutes = 15
    s2.last_fetched_at = now - timedelta(minutes=5)

    # Source 3: fetched 20 mins ago (interval 15) -> due
    s3 = _make_source("s3", name="S3", feed_url="https://s3.com/rss")
    s3.id = source_id3
    s3.fetch_interval_minutes = 15
    s3.last_fetched_at = now - timedelta(minutes=20)

    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [s1, s2, s3]
    session.execute.return_value = mock_result

    service = SourceService(session)
    due = asyncio.run(service.get_due_sources(force=False))

    assert len(due) == 2
    assert [d.name for d in due] == ["S1", "S3"]
    assert isinstance(due[0], DueSource)
    assert due[0].id == source_id1
    assert due[0].feed_url == "https://s1.com/rss"


def test_source_service_get_due_sources_force():
    """Should return all sources when force=True."""
    now = datetime.now(UTC)
    s1 = _make_source("s1", name="S1", feed_url="https://s1.com/rss")
    s1.id = uuid.uuid4()
    s1.fetch_interval_minutes = 15
    s1.last_fetched_at = now - timedelta(minutes=2)

    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [s1]
    session.execute.return_value = mock_result

    service = SourceService(session)
    due = asyncio.run(service.get_due_sources(force=True))

    assert len(due) == 1
    assert due[0].name == "S1"


def test_source_service_records_fetch_success():
    """Success must refresh the timestamp and clear failure state."""
    source_id = uuid.uuid4()
    session = AsyncMock()
    fetched_at = datetime(2026, 1, 2, 3, 4, tzinfo=UTC)

    service = SourceService(session)
    asyncio.run(service.record_fetch_success(source_id, fetched_at=fetched_at))

    stmt = session.execute.call_args.args[0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "last_fetched_at" in compiled
    assert "last_error=NULL" in compiled
    assert "consecutive_failures=0" in compiled
    assert "2026-01-02 03:04:00" in compiled


def test_source_service_records_fetch_failure():
    """Failure must advance the retry anchor and increment the failure counter."""
    source_id = uuid.uuid4()
    session = AsyncMock()
    failed_at = datetime(2026, 1, 2, 3, 4, tzinfo=UTC)

    service = SourceService(session)
    asyncio.run(
        service.record_fetch_failure(
            source_id,
            "ConnectError: feed unreachable",
            failed_at=failed_at,
        )
    )

    stmt = session.execute.call_args.args[0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "last_error='ConnectError: feed unreachable'" in compiled
    assert "consecutive_failures=(sources.consecutive_failures + 1)" in compiled
    assert "2026-01-02 03:04:00" in compiled


def test_source_service_truncates_long_fetch_error():
    """A pathological error must not overflow the source health record."""
    session = AsyncMock()

    service = SourceService(session)
    asyncio.run(service.record_fetch_failure(uuid.uuid4(), "x" * 5000))

    stmt = session.execute.call_args.args[0]
    value = stmt.compile().params["last_error"]
    assert len(value) == 1000


def test_due_sources_apply_failure_backoff():
    """One failure doubles the wait before the next attempt."""
    now = datetime.now(UTC)
    session = AsyncMock()
    result = MagicMock()

    failing = _make_source("failing", feed_url="https://failing.com/rss")
    failing.id = uuid.uuid4()
    failing.fetch_interval_minutes = 15
    failing.last_fetched_at = now - timedelta(minutes=20)
    failing.consecutive_failures = 1

    result.scalars.return_value.all.return_value = [failing]
    session.execute.return_value = result

    due = asyncio.run(SourceService(session).get_due_sources(force=False))

    assert due == []


def test_due_sources_backoff_caps_at_maximum():
    """Persistent failures must stop growing the delay past the cap."""
    now = datetime.now(UTC)
    session = AsyncMock()
    result = MagicMock()

    failing = _make_source("failing", feed_url="https://failing.com/rss")
    failing.id = uuid.uuid4()
    failing.fetch_interval_minutes = 15
    failing.consecutive_failures = 20
    failing.last_fetched_at = now - timedelta(hours=6, minutes=1)

    result.scalars.return_value.all.return_value = [failing]
    session.execute.return_value = result

    due = asyncio.run(SourceService(session).get_due_sources(force=False))

    assert len(due) == 1
    assert due[0].consecutive_failures == 20


def test_due_sources_force_bypasses_backoff():
    """A manual force sync must retry a backed-off source immediately."""
    now = datetime.now(UTC)
    session = AsyncMock()
    result = MagicMock()

    failing = _make_source("failing", feed_url="https://failing.com/rss")
    failing.id = uuid.uuid4()
    failing.fetch_interval_minutes = 15
    failing.last_fetched_at = now - timedelta(minutes=1)
    failing.consecutive_failures = 4

    result.scalars.return_value.all.return_value = [failing]
    session.execute.return_value = result

    due = asyncio.run(SourceService(session).get_due_sources(force=True))

    assert len(due) == 1


def test_due_sources_carry_registry_metadata():
    """Fetch scheduling must expose independence metadata to callers."""
    session = AsyncMock()
    result = MagicMock()

    source = _make_source(
        "bbc-world",
        origin_group="bbc",
        country_code="GB",
        language="en",
    )
    source.id = uuid.uuid4()
    source.fetch_interval_minutes = 15
    source.last_fetched_at = None

    result.scalars.return_value.all.return_value = [source]
    session.execute.return_value = result

    due = asyncio.run(SourceService(session).get_due_sources())

    assert due[0].origin_group == "bbc"
    assert due[0].country_code == "GB"
    assert due[0].language == "en"


def test_source_service_get_due_sources_gdelt():
    """GDELT sources without feed_url must still be returned when due."""
    s_gdelt = _make_source(
        "reuters-wire",
        name="Reuters",
        url="https://reuters.com",
        feed_url=None,
        source_type=SourceType.GDELT,
    )
    s_gdelt.id = uuid.uuid4()
    s_gdelt.fetch_interval_minutes = 15
    s_gdelt.last_fetched_at = None

    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [s_gdelt]
    session.execute.return_value = mock_result

    service = SourceService(session)
    due = asyncio.run(service.get_due_sources(force=False))

    assert len(due) == 1
    assert due[0].name == "Reuters"
    assert due[0].source_type == SourceType.GDELT
    assert due[0].feed_url is None

    session.execute.assert_called_once()
