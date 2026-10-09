"""Tests for hermes_db.services.geocode — GeocodeCacheService.

All tests use a mocked AsyncSession so no database is involved.
"""

from unittest.mock import AsyncMock, MagicMock

from conftest import make_async_session, run

from hermes_db.models.geocode_cache import GeocodeCache
from hermes_db.services.geocode import GeocodeCacheEntry, GeocodeCacheService


# ---------------------------------------------------------------------------
# get_by_location_name
# ---------------------------------------------------------------------------

class TestGetByLocationName:
    def test_returns_cache_entry_when_found(self):
        mock_entry = MagicMock(spec=GeocodeCache)
        mock_entry.location_name = "london"
        mock_entry.latitude = 51.5074
        mock_entry.longitude = -0.1278
        mock_entry.display_name = "London, UK"
        session = make_async_session(execute_scalar_one_or_none=mock_entry)
        svc = GeocodeCacheService(session)

        result = run(svc.get_by_location_name("  London  "))

        assert result == GeocodeCacheEntry(
            location_name="london",
            latitude=51.5074,
            longitude=-0.1278,
            display_name="London, UK",
        )
        session.execute.assert_awaited_once()


    def test_normalizes_location_name(self):
        session = make_async_session(execute_scalar_one_or_none=None)
        svc = GeocodeCacheService(session)

        result = run(svc.get_by_location_name("  New York  "))
        assert result is None
        session.execute.assert_awaited_once()


    def test_returns_none_when_not_found(self):
        session = make_async_session(execute_scalar_one_or_none=None)
        svc = GeocodeCacheService(session)

        result = run(svc.get_by_location_name("Unknown"))
        assert result is None
        session.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# save_geocode_result
# ---------------------------------------------------------------------------

class TestSaveGeocodeResult:
    def _make_svc_with_entry(
        self, entry: GeocodeCache | None
    ) -> tuple[GeocodeCacheService, AsyncMock]:
        """Wire a session mock so both execute() calls return appropriately.

        The upsert (first execute) uses its result for nothing meaningful.
        The re-fetch SELECT (second execute) must return the GeocodeCache entry
        via scalar_one_or_none().  We set the same return value for all calls
        since the mock returns the same result object each time — that's fine
        because the upsert result is never read.
        """
        session = make_async_session(execute_scalar_one_or_none=entry)
        return GeocodeCacheService(session), session


    def test_returns_geocode_cache_instance(self):
        """save_geocode_result must return the re-fetched GeocodeCacheEntry."""
        mock_entry = MagicMock(spec=GeocodeCache)
        mock_entry.location_name = "paris"
        mock_entry.latitude = 48.8566
        mock_entry.longitude = 2.3522
        mock_entry.display_name = "Paris, France"

        svc, _ = self._make_svc_with_entry(mock_entry)
        result = run(
            svc.save_geocode_result(
                location_name=" Paris ",
                latitude=48.8566,
                longitude=2.3522,
                display_name="Paris, France",
            )
        )
        assert result == GeocodeCacheEntry(
            location_name="paris",
            latitude=48.8566,
            longitude=2.3522,
            display_name="Paris, France",
        )


    def test_execute_called_twice_and_committed(self):
        """Must issue two executes (upsert + re-fetch SELECT) and commit exactly once."""
        mock_entry = MagicMock(spec=GeocodeCache)
        mock_entry.location_name = "berlin"
        mock_entry.latitude = 52.5200
        mock_entry.longitude = 13.4050
        mock_entry.display_name = "Berlin, Germany"
        svc, session = self._make_svc_with_entry(mock_entry)
        run(
            svc.save_geocode_result(
                location_name="Berlin",
                latitude=52.5200,
                longitude=13.4050,
                display_name="Berlin, Germany",
            )
        )
        assert session.execute.await_count == 2
        session.commit.assert_awaited_once()


    def test_does_not_call_session_add(self):
        """Upsert path must not use session.add()."""
        mock_entry = MagicMock(spec=GeocodeCache)
        mock_entry.location_name = "tokyo"
        mock_entry.latitude = 35.6762
        mock_entry.longitude = 139.6503
        mock_entry.display_name = "Tokyo, Japan"
        svc, session = self._make_svc_with_entry(mock_entry)
        run(
            svc.save_geocode_result(
                location_name="Tokyo",
                latitude=35.6762,
                longitude=139.6503,
                display_name="Tokyo, Japan",
            )
        )
        session.add.assert_not_called()

