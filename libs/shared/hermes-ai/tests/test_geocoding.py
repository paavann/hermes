import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from hermes_ai.client import HermesAiClient
from hermes_ai.core.config import AiConfig
from hermes_ai.models.events import ArticleInput, GroundedEvent
from hermes_ai.models.tl import GroundedTlNode
from hermes_ai.services.geocoding import (
    _NOT_FOUND,
    GeocodeCacheEntry,
    GeocodingResult,
    GeocodingService,
    NominatimResilienceManager,
    clean_location_name,
)


class DummyCacheEntry:
    def __init__(
        self,
        latitude: float | None,
        longitude: float | None,
        display_name: str | None,
    ) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.display_name = display_name


class DummyCache:
    def __init__(self) -> None:
        self.store: dict[str, DummyCacheEntry] = {}
        self.save_calls: list[tuple[str, float | None, float | None, str | None]] = []

    async def get_by_location_name(
        self, location_name: str
    ) -> GeocodeCacheEntry | None:
        return self.store.get(location_name)

    async def save_geocode_result(
        self,
        location_name: str,
        latitude: float | None,
        longitude: float | None,
        display_name: str | None,
    ) -> object:
        self.save_calls.append((location_name, latitude, longitude, display_name))
        entry = DummyCacheEntry(latitude, longitude, display_name)
        self.store[location_name] = entry
        return entry


def test_clean_location_name() -> None:
    assert clean_location_name("Multiple cities (e.g., Cairo, Giza)") == "Cairo"
    assert clean_location_name("Berlin (city center)") == "Berlin"
    assert clean_location_name("Syria (nationwide)") == "Syria"
    assert clean_location_name("Tokyo") == "Tokyo"
    assert clean_location_name("Global") is None
    assert clean_location_name("Multiple locations") is None
    assert clean_location_name("Worldwide") is None
    assert clean_location_name("Unknown") is None
    assert clean_location_name("   ") is None
    assert clean_location_name("") is None


def test_geocoding_service_cache_hit() -> None:
    async def _run() -> None:
        cache = DummyCache()
        cache.store["rome, italy"] = DummyCacheEntry(41.9028, 12.4964, "Rome, Italy")
        service = GeocodingService(cache_service=cache)

        with patch.object(service, "_call_nominatim") as mock_call:
            res = await service.geocode("Rome, Italy")
            assert res is not None
            assert res.latitude == 41.9028
            assert res.longitude == 12.4964
            mock_call.assert_not_called()

    asyncio.run(_run())


def test_geocoding_service_negative_cache_hit() -> None:
    async def _run() -> None:
        cache = DummyCache()
        cache.store["nowhere"] = DummyCacheEntry(None, None, None)
        service = GeocodingService(cache_service=cache)

        with patch.object(service, "_call_nominatim") as mock_call:
            res = await service.geocode("Nowhere")
            assert res is None
            mock_call.assert_not_called()

    asyncio.run(_run())


def test_geocoding_service_fetches_and_persists() -> None:
    async def _run() -> None:
        cache = DummyCache()
        service = GeocodingService(cache_service=cache)
        expected = GeocodingResult(35.6762, 139.6503, "Tokyo, Japan")

        with patch.object(
            service, "_call_nominatim", new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = expected
            res = await service.geocode("Tokyo, Japan")
            assert res == expected
            assert len(cache.save_calls) == 1
            assert cache.save_calls[0] == (
                "tokyo, japan",
                35.6762,
                139.6503,
                "Tokyo, Japan",
            )

    asyncio.run(_run())


def test_geocoding_service_negative_cache_on_not_found() -> None:
    async def _run() -> None:
        cache = DummyCache()
        service = GeocodingService(cache_service=cache)

        with patch.object(
            service, "_call_nominatim", new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = _NOT_FOUND
            res = await service.geocode("Fantasy Land 9999")
            assert res is None
            assert len(cache.save_calls) == 1
            assert cache.save_calls[0] == ("fantasy land 9999", None, None, None)

    asyncio.run(_run())


def test_geocoding_service_transient_error_does_not_poison_cache() -> None:
    async def _run() -> None:
        cache = DummyCache()
        service = GeocodingService(cache_service=cache)

        with patch.object(
            service, "_call_nominatim", new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = None  # transient 429 / timeout
            res = await service.geocode("Brisbane, Australia")
            assert res is None
            # Must not persist negative cache for transient error!
            assert len(cache.save_calls) == 0

    asyncio.run(_run())


def test_geocoding_service_deduplicates_in_flight() -> None:
    async def _run() -> None:
        cache = DummyCache()
        service = GeocodingService(cache_service=cache)
        expected = GeocodingResult(40.7128, -74.006, "New York, USA")

        async def _delayed_call(name: str) -> GeocodingResult:
            await asyncio.sleep(0.05)
            return expected

        with patch.object(
            service, "_call_nominatim", side_effect=_delayed_call
        ) as mock_call:
            results = await asyncio.gather(
                service.geocode("New York, USA"),
                service.geocode("New York, USA"),
            )
            assert results[0] == expected
            assert results[1] == expected
            assert mock_call.call_count == 1

    asyncio.run(_run())


def test_resilience_manager_circuit_breaker() -> None:
    async def _run() -> None:
        manager = NominatimResilienceManager(
            min_request_interval=0.01, circuit_cooldown_seconds=10.0
        )
        assert not manager.is_circuit_open()[0]
        manager.trip_circuit_breaker()
        is_open, remaining = manager.is_circuit_open()
        assert is_open
        assert remaining > 0.0

    asyncio.run(_run())


def test_call_nominatim_retries_on_429() -> None:
    async def _run() -> None:
        client = AsyncMock(spec=httpx.AsyncClient)
        res_429 = MagicMock()
        res_429.status_code = 429
        res_429.headers = {"Retry-After": "0"}

        res_ok = MagicMock()
        res_ok.status_code = 200
        res_ok.json.return_value = [
            {"lat": "51.5074", "lon": "-0.1278", "display_name": "London, UK"}
        ]

        client.get = AsyncMock(side_effect=[res_429, res_ok])
        service = GeocodingService(client=client, min_interval=0.0)
        res = await service.geocode("London, UK")
        assert res is not None
        assert res.latitude == 51.5074
        assert res.longitude == -0.1278
        assert client.get.call_count == 2

    asyncio.run(_run())


def test_autonomous_grounding_in_event_extractor() -> None:
    async def _run() -> None:
        config = AiConfig(
            primary_model="mistral/mistral-large",
            primary_api_key="key",
        )
        client = HermesAiClient(config)
        geo_service = GeocodingService()

        # Mock LLM response with location
        json_content = (
            '{"events": [{"article_index": 0, "has_location": true, "location_name": '
            '"Paris, France", "country_code": "FR", "headline": "Summit in Paris", '
            '"summary": "World leaders meet in Paris.", "category": "POLITICS"}]}'
        )
        mock_msg = AsyncMock(content=json_content)
        mock_res = AsyncMock(choices=[AsyncMock(message=mock_msg)])
        client._router.acompletion = AsyncMock(return_value=mock_res)

        with patch.object(
            geo_service,
            "geocode",
            new_callable=AsyncMock,
            return_value=GeocodingResult(48.8566, 2.3522, "Paris, France"),
        ) as mock_geo:
            articles = [ArticleInput(title="Paris Summit", content="Meeting details")]
            events = await client.extract_events(articles, geocoding_svc=geo_service)
            assert len(events) == 1
            event = events[0]
            assert isinstance(event, GroundedEvent)
            assert event.latitude == 48.8566
            assert event.longitude == 2.3522
            mock_geo.assert_awaited_once_with("Paris, France")

    asyncio.run(_run())


def test_autonomous_grounding_in_tl_extractor() -> None:
    async def _run() -> None:
        config = AiConfig(
            primary_model="mistral/mistral-large",
            primary_api_key="key",
        )
        client = HermesAiClient(config)
        geo_service = GeocodingService()

        tl_json = (
            '{"tl_summary": "Historical overview.", "nodes": [{"date": "1944-08-25", '
            '"headline": "Liberation of Paris", "location_name": "Paris, France", '
            '"summary": "Allied forces liberate Paris."}], "edges": []}'
        )
        mock_msg = AsyncMock(content=tl_json)
        mock_res = AsyncMock(choices=[AsyncMock(message=mock_msg)])
        client._router.acompletion = AsyncMock(return_value=mock_res)

        with patch.object(
            geo_service,
            "geocode",
            new_callable=AsyncMock,
            return_value=GeocodingResult(48.8566, 2.3522, "Paris, France"),
        ):
            tl = await client.extract_tl(
                pg_title="Liberation_of_Paris",
                prose="Historical text...",
                geocoding_svc=geo_service,
            )
            assert tl is not None
            assert len(tl.nodes) == 1
            node = tl.nodes[0]
            assert isinstance(node, GroundedTlNode)
            assert node.latitude == 48.8566
            assert node.longitude == 2.3522

    asyncio.run(_run())
