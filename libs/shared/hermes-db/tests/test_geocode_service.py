"""Tests for hermes_db.services.geocode — GeocodeCacheService.

All tests use a mocked AsyncSession so no database is involved.
"""

from unittest.mock import AsyncMock, MagicMock

from conftest import make_async_session, run

from hermes_db.models.geocode_cache import GeocodeCache
from hermes_db.services.geocode import GeocodeCacheService


# ---------------------------------------------------------------------------
# get_by_location_name
# ---------------------------------------------------------------------------

class TestGetByLocationName:
    def test_returns_cache_entry_when_found(self):
        mock_entry = MagicMock(spec=GeocodeCache)
        session = make_async_session(execute_scalar_one_or_none=mock_entry)
        svc = GeocodeCacheService(session)
        
        result = run(svc.get_by_location_name("  London  "))
        
        assert result is mock_entry
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
    def _make_svc(self) -> tuple[GeocodeCacheService, AsyncMock]:
        session = make_async_session()
        return GeocodeCacheService(session), session

    def test_returns_geocode_cache_instance(self):
        svc, session = self._make_svc()
        result = run(
            svc.save_geocode_result(
                location_name=" Paris ",
                latitude=48.8566,
                longitude=2.3522,
                display_name="Paris, France"
            )
        )
        assert isinstance(result, GeocodeCache)
        assert result.location_name == "paris"
        assert result.latitude == 48.8566
        assert result.longitude == 2.3522
        assert result.display_name == "Paris, France"

    def test_entry_added_to_session_and_committed(self):
        svc, session = self._make_svc()
        result = run(
            svc.save_geocode_result(
                location_name="Berlin",
                latitude=52.5200,
                longitude=13.4050,
                display_name="Berlin, Germany"
            )
        )
        session.add.assert_called_once_with(result)
        session.commit.assert_awaited_once()
