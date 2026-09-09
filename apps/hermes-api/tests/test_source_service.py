"""Tests for the source sync service.

These tests mock the database layer and file system to validate
the upsert/disable logic in isolation.
"""

import asyncio
import json
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from hermes_api.services.source_service import (
    sync_sources_from_config,
    _load_sources_config,
)
from hermes_api.db.models.source import Source


# --- Helpers ---

def _make_source(
    slug: str,
    name: str = "Test",
    url: str = "https://example.com",
    feed_url: str = "https://example.com/rss",
    credibility: str = "TIER_3",
    is_active: bool = True,
) -> MagicMock:
    """Create a mock Source ORM object."""
    source = MagicMock(spec=Source)
    source.slug = slug
    source.name = name
    source.url = url
    source.feed_url = feed_url
    source.credibility = credibility
    source.is_active = is_active
    return source


def _mock_session(
    existing_sources: Optional[list] = None,
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
        idx = call_counter["n"]
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


# --- Tests for _load_sources_config ---

def test_load_sources_config_valid():
    """Should parse a valid JSON array from the config file."""
    sample = [{"slug": "bbc-world", "name": "BBC World"}]

    with patch.object(Path, "read_text", return_value=json.dumps(sample)):
        result = asyncio.run(_load_sources_config())
        assert result == sample


def test_load_sources_config_not_a_list():
    """Should raise ValueError if the JSON is not an array."""
    import pytest

    with patch.object(Path, "read_text", return_value='{"slug": "bbc"}'):
        with pytest.raises(ValueError, match="JSON array"):
            asyncio.run(_load_sources_config())


def test_load_sources_config_file_not_found():
    """Should raise FileNotFoundError if the file is missing."""
    import pytest

    with patch.object(Path, "read_text", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            asyncio.run(_load_sources_config())


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
        }
    ]
    session = _mock_session(existing_sources=[])

    with patch(
        "hermes_api.services.source_service._load_sources_config",
        new_callable=AsyncMock,
        return_value=config,
    ):
        stats = asyncio.run(sync_sources_from_config(session))

    assert stats["inserted"] == 1
    assert stats["updated"] == 0
    assert stats["disabled"] == 0
    session.add.assert_called_once()


def test_sync_skips_entries_without_slug():
    """Entries missing a slug should be skipped with a warning."""
    config = [{"name": "No Slug Source", "url": "https://example.com"}]
    session = _mock_session(existing_sources=[])

    with patch(
        "hermes_api.services.source_service._load_sources_config",
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
        "hermes_api.services.source_service._load_sources_config",
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
        "hermes_api.services.source_service._load_sources_config",
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
        "hermes_api.services.source_service._load_sources_config",
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
    )
    session = _mock_session(existing_sources=[existing])

    with patch(
        "hermes_api.services.source_service._load_sources_config",
        new_callable=AsyncMock,
        return_value=config,
    ):
        stats = asyncio.run(sync_sources_from_config(session))

    # Nothing should change — already in sync.
    assert stats["inserted"] == 0
    assert stats["disabled"] == 0
    session.add.assert_not_called()
