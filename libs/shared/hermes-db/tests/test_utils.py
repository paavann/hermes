"""Tests for hermes_db.utils."""

from datetime import UTC, datetime, timedelta, timezone

from hermes_db.utils.datetime import ensure_utc


class TestEnsureUtc:
    def test_attaches_utc_to_naive_datetime(self) -> None:
        naive = datetime(2026, 11, 10, 12, 30, 0)
        assert ensure_utc(naive) == datetime(2026, 11, 10, 12, 30, 0, tzinfo=UTC)

    def test_converts_non_utc_offset_to_utc(self) -> None:
        ist = timezone(timedelta(hours=5, minutes=30))
        local = datetime(2026, 11, 10, 18, 0, 0, tzinfo=ist)
        assert ensure_utc(local) == datetime(2026, 11, 10, 12, 30, 0, tzinfo=UTC)
