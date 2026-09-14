"""Tests for the Wikipedia MediaWiki Action API client.

All tests mock the httpx layer so no real network calls are made.
The test surface covers:
- search_timeline_titles: happy path, empty results, HTTP error, parse error.
- fetch_page_extracts: single title, multi-title batching, missing pages,
  empty extracts, title normalisation, HTTP error.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hermes_api.services.wikipedia_service import (
    _MAX_TITLES_PER_REQUEST,
    fetch_page_extracts,
    search_timeline_titles,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_httpx_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Build a mock httpx.Response-like object."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        import httpx
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=response
        )
    return response


def _search_response(titles: list[str]) -> dict:
    """Build a minimal MediaWiki search API response."""
    return {
        "query": {
            "search": [{"title": t, "pageid": i + 1} for i, t in enumerate(titles)]
        }
    }


def _extracts_response(pages: list[dict[str, Any]]) -> dict:
    """Build a minimal MediaWiki extracts API response (formatversion=2)."""
    return {"query": {"pages": pages}}


def _page(title: str, extract: str, missing: bool = False) -> dict:
    """Build a single page entry for an extracts response."""
    entry: dict = {"title": title, "id": -1 if missing else 1, "extract": extract}
    if missing:
        entry["missing"] = True
    return entry


# ---------------------------------------------------------------------------
# search_timeline_titles
# ---------------------------------------------------------------------------


class TestSearchTimelineTitles:
    """Tests for the intitle search function."""

    def test_returns_titles_on_success(self) -> None:
        """Should return a list of page titles from a successful search."""
        mock_resp = _mock_httpx_response(
            _search_response(
                [
                    "Timeline of the Israel–Gaza war",
                    "Timeline of the Israel–Gaza war (2024)",
                ]
            )
        )
        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = asyncio.run(
                search_timeline_titles("Timeline of the Israel–Gaza war")
            )

        assert result == [
            "Timeline of the Israel–Gaza war",
            "Timeline of the Israel–Gaza war (2024)",
        ]

    def test_returns_empty_list_on_no_results(self) -> None:
        """Should return an empty list when the search finds nothing."""
        mock_resp = _mock_httpx_response(_search_response([]))
        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = asyncio.run(search_timeline_titles("nonexistent story xyz"))

        assert result == []

    def test_returns_empty_list_on_http_error(self) -> None:
        """Should return an empty list (not raise) on HTTP failure."""
        import httpx

        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.HTTPError("connection failed")
            )
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = asyncio.run(search_timeline_titles("anything"))

        assert result == []

    def test_respects_limit_cap(self) -> None:
        """The srlimit param should never exceed _MAX_TITLES_PER_REQUEST."""
        mock_resp = _mock_httpx_response(_search_response([]))
        captured_params: list[dict] = []

        async def capturing_get(url: str, **kwargs: Any) -> MagicMock:
            captured_params.append(kwargs.get("params", {}))
            return mock_resp

        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = capturing_get
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            # Request 999 results — should be capped.
            asyncio.run(search_timeline_titles("test", limit=999))

        assert captured_params[0]["srlimit"] == _MAX_TITLES_PER_REQUEST

    def test_user_agent_is_set(self) -> None:
        """Every request must include a User-Agent header."""
        mock_resp = _mock_httpx_response(_search_response([]))
        captured_headers: list[dict] = []

        async def capturing_get(url: str, **kwargs: Any) -> MagicMock:
            captured_headers.append(kwargs.get("headers", {}))
            return mock_resp

        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = capturing_get
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            asyncio.run(search_timeline_titles("test"))

        assert "User-Agent" in captured_headers[0]
        assert len(captured_headers[0]["User-Agent"]) > 0


# ---------------------------------------------------------------------------
# fetch_page_extracts
# ---------------------------------------------------------------------------


class TestFetchPageExtracts:
    """Tests for the batched extract fetcher."""

    def test_returns_extract_for_single_title(self) -> None:
        """Should return a dict with the page's extract for one title."""
        extract_text = "== January ==\n* 7 January – Israeli forces..."
        mock_resp = _mock_httpx_response(
            _extracts_response(
                [_page("Timeline of the Israel–Gaza war", extract_text)]
            )
        )
        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = asyncio.run(
                fetch_page_extracts(["Timeline of the Israel–Gaza war"])
            )

        assert result["Timeline of the Israel–Gaza war"] == extract_text

    def test_returns_none_for_missing_page(self) -> None:
        """A page marked missing in the API response should map to None."""
        mock_resp = _mock_httpx_response(
            _extracts_response(
                [_page("NonExistent Page", "", missing=True)]
            )
        )
        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = asyncio.run(fetch_page_extracts(["NonExistent Page"]))

        assert result["NonExistent Page"] is None

    def test_returns_none_for_empty_extract(self) -> None:
        """A page that exists but has an empty extract should map to None."""
        mock_resp = _mock_httpx_response(
            _extracts_response([_page("Empty Page", "   ")])
        )
        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = asyncio.run(fetch_page_extracts(["Empty Page"]))

        assert result["Empty Page"] is None

    def test_batches_more_than_50_titles(self) -> None:
        """Requests for > 50 titles must be split into multiple HTTP calls."""
        titles = [f"Page {i}" for i in range(75)]
        call_count = 0

        async def counting_get(url: str, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            # Return an empty pages list for every batch.
            return _mock_httpx_response(_extracts_response([]))

        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = counting_get
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            asyncio.run(fetch_page_extracts(titles))

        # 75 titles → 2 batches (50 + 25).
        assert call_count == 2

    def test_deduplicates_titles(self) -> None:
        """Duplicate titles in the input must not produce duplicate requests."""
        call_count = 0

        async def counting_get(url: str, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            return _mock_httpx_response(_extracts_response([]))

        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = counting_get
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            # Three duplicates of the same title → should result in one request.
            asyncio.run(fetch_page_extracts(["Gaza War", "Gaza War", "Gaza War"]))

        assert call_count == 1

    def test_returns_empty_dict_for_empty_input(self) -> None:
        """An empty titles list should return an empty dict without making a request."""
        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            result = asyncio.run(fetch_page_extracts([]))

        mock_client_cls.assert_not_called()
        assert result == {}

    def test_returns_none_values_on_http_error(self) -> None:
        """All requested titles should map to None (not raise) on HTTP failure."""
        import httpx

        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.HTTPError("timeout")
            )
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = asyncio.run(fetch_page_extracts(["Page A", "Page B"]))

        assert result["Page A"] is None
        assert result["Page B"] is None

    def test_user_agent_is_set_on_extract_request(self) -> None:
        """Every extract request must include a User-Agent header."""
        captured_headers: list[dict] = []

        async def capturing_get(url: str, **kwargs: Any) -> MagicMock:
            captured_headers.append(kwargs.get("headers", {}))
            return _mock_httpx_response(_extracts_response([]))

        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = capturing_get
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            asyncio.run(fetch_page_extracts(["Any Page"]))

        assert "User-Agent" in captured_headers[0]
        assert len(captured_headers[0]["User-Agent"]) > 0

    def test_resolves_title_normalisation(self) -> None:
        """Titles returned by Wikipedia with different casing should still
        map back to the caller's original key."""
        # Caller requests "timeline of the israel–gaza war" (lowercase)
        # but Wikipedia returns "Timeline of the Israel–Gaza war" (title case).
        extract_text = "January 2024..."
        wiki_returned_title = "Timeline of the Israel–Gaza war"
        caller_title = "timeline of the israel–gaza war"

        mock_resp = _mock_httpx_response(
            _extracts_response([_page(wiki_returned_title, extract_text)])
        )
        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = asyncio.run(fetch_page_extracts([caller_title]))

        # The extract must be accessible via the caller's own key.
        assert result[caller_title] == extract_text


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Cross-cutting edge cases."""

    def test_multiple_titles_all_resolved(self) -> None:
        """Multiple valid titles in a single batch should all be resolved."""
        pages = [
            _page("Page A", "Content A"),
            _page("Page B", "Content B"),
        ]
        mock_resp = _mock_httpx_response(_extracts_response(pages))
        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = asyncio.run(fetch_page_extracts(["Page A", "Page B"]))

        assert result["Page A"] == "Content A"
        assert result["Page B"] == "Content B"

    def test_mixed_valid_and_missing_pages(self) -> None:
        """In one batch, valid and missing pages should be handled independently."""
        pages = [
            _page("Good Page", "Has content"),
            _page("Bad Page", "", missing=True),
        ]
        mock_resp = _mock_httpx_response(_extracts_response(pages))
        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = asyncio.run(fetch_page_extracts(["Good Page", "Bad Page"]))

        assert result["Good Page"] == "Has content"
        assert result["Bad Page"] is None

    @pytest.mark.parametrize("n_titles,expected_batches", [
        (1, 1),
        (50, 1),
        (51, 2),
        (100, 2),
        (101, 3),
    ])
    def test_batch_count(self, n_titles: int, expected_batches: int) -> None:
        """The number of HTTP calls must match the expected batch count."""
        call_count = 0

        async def counting_get(url: str, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            return _mock_httpx_response(_extracts_response([]))

        with patch(
            "hermes_api.services.wikipedia_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = counting_get
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            asyncio.run(fetch_page_extracts([f"Page {i}" for i in range(n_titles)]))

        assert call_count == expected_batches
