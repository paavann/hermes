"""Tests for GeocodingService rate limiting, caching, and 429 backoff."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hermes_api.db.models.geocode_cache import GeocodeCache
from hermes_api.services import geocoding_service
from hermes_api.services.geocoding_service import (
    _NOT_FOUND,
    GeocodingResult,
    GeocodingService,
    clean_location_name,
)


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


class TestGeocodingService:
    def test_cache_hit_returns_immediately(self, mock_session):
        async def run():
            mock_cache_entry = GeocodeCache(
                location_name="paris, france",
                latitude=48.8566,
                longitude=2.3522,
                display_name="Paris, France",
            )
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_cache_entry
            mock_session.execute.return_value = mock_result

            service = GeocodingService()
            with patch.object(service, "_call_nominatim") as mock_call:
                res = await service.geocode(mock_session, "Paris, France")
                assert res is not None
                assert res.latitude == 48.8566
                assert res.longitude == 2.3522
                mock_call.assert_not_called()

        asyncio.run(run())

    def test_successful_geocoding_persists_cache(self, mock_session):
        async def run():
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            service = GeocodingService()
            expected = GeocodingResult(
                latitude=51.5074,
                longitude=-0.1278,
                display_name="London, Greater London, England, United Kingdom",
            )

            with patch.object(service, "_call_nominatim", new_callable=AsyncMock) as mock_call:
                mock_call.return_value = expected
                res = await service.geocode(mock_session, "London, UK")

                assert res == expected
                mock_session.add.assert_called_once()
                saved_cache = mock_session.add.call_args[0][0]
                assert saved_cache.location_name == "london, uk"
                assert saved_cache.latitude == 51.5074
                mock_session.commit.assert_awaited_once()

        asyncio.run(run())

    def test_empty_results_persists_negative_cache(self, mock_session):
        async def run():
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            service = GeocodingService()

            with patch.object(service, "_call_nominatim", new_callable=AsyncMock) as mock_call:
                mock_call.return_value = _NOT_FOUND
                res = await service.geocode(mock_session, "Nonexistent Place 12345")

                assert res is None
                mock_session.add.assert_called_once()
                saved_cache = mock_session.add.call_args[0][0]
                assert saved_cache.latitude is None
                assert saved_cache.longitude is None
                mock_session.commit.assert_awaited_once()

        asyncio.run(run())

    def test_transient_failure_does_not_persist_cache(self, mock_session):
        async def run():
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            service = GeocodingService()

            with patch.object(service, "_call_nominatim", new_callable=AsyncMock) as mock_call:
                mock_call.return_value = None  # transient 429 / error
                res = await service.geocode(mock_session, "Brisbane, Australia")

                assert res is None
                mock_session.add.assert_not_called()
                mock_session.commit.assert_not_awaited()

        asyncio.run(run())

    @patch("asyncio.sleep", new_callable=AsyncMock)
    def test_call_nominatim_retries_on_429(self, mock_sleep):
        async def run():
            service = GeocodingService()

            # First attempt 429, second attempt 200 with result
            mock_resp_429 = MagicMock()
            mock_resp_429.status_code = 429
            mock_resp_429.headers = {"Retry-After": "1"}

            mock_resp_200 = MagicMock()
            mock_resp_200.status_code = 200
            mock_resp_200.raise_for_status = MagicMock()
            mock_resp_200.json.return_value = [
                {"lat": "-27.4698", "lon": "153.0251", "display_name": "Brisbane, Australia"}
            ]

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[mock_resp_429, mock_resp_200])

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__.return_value = mock_client
                res = await service._call_nominatim("Brisbane, Australia")

                assert isinstance(res, GeocodingResult)
                assert res.latitude == -27.4698
                assert res.longitude == 153.0251
                assert mock_client.get.call_count == 2
                assert mock_sleep.await_count >= 1

        asyncio.run(run())

    def test_clean_location_name_sanitizes_complex_strings(self):
        assert clean_location_name("Multiple cities (e.g., Sanaa, Taiz)") == "Sanaa"
        assert clean_location_name("Sanaa (mosque)") == "Sanaa"
        assert clean_location_name("Yemen (nationwide)") == "Yemen"
        assert clean_location_name("Southern Yemen (e.g., Aden)") == "Aden"
        assert clean_location_name("Aden") == "Aden"
        assert clean_location_name("Various locations") is None
        assert clean_location_name("Nationwide") is None
        assert clean_location_name("") is None

    @patch("asyncio.sleep", new_callable=AsyncMock)
    def test_circuit_breaker_trips_on_persistent_429(self, mock_sleep):
        async def run():
            service = GeocodingService()
            mock_resp_429 = MagicMock()
            mock_resp_429.status_code = 429
            mock_resp_429.headers = {"Retry-After": "0"}

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp_429)

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__.return_value = mock_client
                res = await service._call_nominatim("Blocked Location", max_retries=2)
                assert res is None
                # Verify circuit breaker is now active
                assert geocoding_service._circuit_open_until > time.monotonic()

                # Subsequent call should immediately return None without calling httpx
                mock_client.get.reset_mock()
                fast_res = await service._call_nominatim("Another Location")
                assert fast_res is None
                mock_client.get.assert_not_called()

            # Reset circuit breaker for subsequent tests
            geocoding_service._circuit_open_until = 0.0

        asyncio.run(run())
