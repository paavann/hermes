"""Unit tests for hermes_worker.services.geocoding client, location cleaner, and cache integration."""

import asyncio
from unittest.mock import AsyncMock, patch
import pytest
from hermes_db.models import GeocodeCache
from hermes_db.services import GeocodeCacheService
from hermes_worker.services.geocoding import (
    GeocodingResult,
    GeocodingService,
    clean_location_name,
)


@pytest.fixture
def mock_cache_service():
    service = AsyncMock(spec=GeocodeCacheService)
    service.get_by_location_name = AsyncMock(return_value=None)
    service.save_geocode_result = AsyncMock()
    return service


class TestCleanLocationName:
    def test_clean_location_name_sanitizes_strings(self):
        assert clean_location_name("Multiple cities (e.g., Cairo, Giza)") == "Cairo"
        assert clean_location_name("Berlin (city center)") == "Berlin"
        assert clean_location_name("Syria (nationwide)") == "Syria"
        assert clean_location_name("Tokyo") == "Tokyo"
        assert clean_location_name("Global") is None
        assert clean_location_name("Multiple locations") is None
        assert clean_location_name("Worldwide") is None
        assert clean_location_name("   ") is None
        assert clean_location_name("") is None


class TestWorkerGeocodingService:
    def test_geocode_returns_cached_hit(self, mock_cache_service):
        async def run():
            cached_entry = GeocodeCache(
                location_name="rome, italy",
                latitude=41.9028,
                longitude=12.4964,
                display_name="Rome, Italy",
            )
            mock_cache_service.get_by_location_name.return_value = cached_entry

            service = GeocodingService(mock_cache_service)
            with patch.object(service, "_call_nominatim") as mock_nominatim:
                res = await service.geocode("Rome, Italy")
                assert res is not None
                assert res.latitude == 41.9028
                assert res.longitude == 12.4964
                mock_nominatim.assert_not_called()

        asyncio.run(run())

    def test_geocode_fetches_and_persists_on_cache_miss(self, mock_cache_service):
        async def run():
            service = GeocodingService(mock_cache_service)
            expected = GeocodingResult(
                latitude=35.6762,
                longitude=139.6503,
                display_name="Tokyo, Japan",
            )

            with patch.object(
                service, "_call_nominatim", new_callable=AsyncMock
            ) as mock_nominatim:
                mock_nominatim.return_value = expected
                res = await service.geocode("Tokyo, Japan")

                assert res == expected
                mock_cache_service.save_geocode_result.assert_awaited_once_with(
                    location_name="tokyo, japan",
                    latitude=35.6762,
                    longitude=139.6503,
                    display_name="Tokyo, Japan",
                )

        asyncio.run(run())

    def test_geocode_persists_negative_cache_on_none_result(self, mock_cache_service):
        async def run():
            service = GeocodingService(mock_cache_service)

            with patch.object(
                service, "_call_nominatim", new_callable=AsyncMock
            ) as mock_nominatim:
                mock_nominatim.return_value = None
                res = await service.geocode("Unreachable Fantasy Land")

                assert res is None
                mock_cache_service.save_geocode_result.assert_awaited_once_with(
                    location_name="unreachable fantasy land",
                    latitude=None,
                    longitude=None,
                    display_name=None,
                )

        asyncio.run(run())

    def test_geocode_deduplicates_in_flight_requests(self, mock_cache_service):
        async def run():
            service = GeocodingService(mock_cache_service)
            expected = GeocodingResult(
                latitude=40.7128,
                longitude=-74.0060,
                display_name="New York, USA",
            )

            call_count = 0

            async def slow_nominatim(loc):
                nonlocal call_count
                call_count += 1
                await asyncio.sleep(0.05)
                return expected

            with patch.object(service, "_call_nominatim", side_effect=slow_nominatim):
                # Issue two concurrent requests for the exact same location
                res1, res2 = await asyncio.gather(
                    service.geocode("New York, USA"),
                    service.geocode("New York, USA"),
                )
                assert res1 == expected
                assert res2 == expected
                # Nominatim should only have been called once due to in-flight deduplication
                assert call_count == 1

        asyncio.run(run())
