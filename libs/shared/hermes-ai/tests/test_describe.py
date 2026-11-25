from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from hermes_ai.core.config import AiConfig, ModelRoute, ModelTarget
from hermes_ai.extractors.describe import DescribeExtractor
from hermes_ai.models.describe import (
    DescribeEventInput,
    DescribeImpact,
    DescribeMemberFact,
    EventDescription,
    EventDescriptionBatchResponse,
)
from hermes_ai.models.labels import LabelLocation, LabelScope
from hermes_ai.services.llm import LlmService


def _config() -> AiConfig:
    target = ModelTarget(model="nvidia_nim/test-model", api_key="test-key")
    return AiConfig(routes={"describe": ModelRoute(primary=target)})


def _item(
    index: int,
    *,
    fact: str,
    source: str = "Reuters",
    published_at: str | None = "2026-11-05T10:48:00Z",
) -> DescribeEventInput:
    return DescribeEventInput(
        index=index,
        category="TECHNOLOGY",
        facts=[
            DescribeMemberFact(
                fact=fact,
                source=source,
                published_at=published_at,
                entities=["Nvidia"],
                locations=["Silicon Valley"],
            )
        ],
    )


def _description(
    index: int,
    *,
    headline: str,
    summary: str,
) -> EventDescription:
    return EventDescription(
        index=index,
        headline=headline,
        summary=summary,
        impact_level=DescribeImpact.MINOR,
        scope=LabelScope.CITY,
        locations=[LabelLocation(name="Silicon Valley", country_code="US")],
    )


def test_describe_allows_published_at_date_and_source_numbers_without_retry() -> None:
    async def _run() -> None:
        svc = LlmService(_config())
        extractor = DescribeExtractor(svc)
        batch = EventDescriptionBatchResponse(
            descriptions=[
                _description(
                    0,
                    headline="Nvidia chief returns in Silicon Valley",
                    summary=(
                        "Nvidia's CEO returned on November 5, 2026, "
                        "according to France 24 reporting."
                    ),
                )
            ]
        )
        with patch.object(
            svc, "complete_json", new_callable=AsyncMock, return_value=batch
        ) as mock_call:
            result = await extractor.describe(
                [
                    _item(
                        0,
                        fact="Nvidia CEO returned to office in Silicon Valley.",
                        source="France 24",
                        published_at="2026-11-05T10:48:00Z",
                    )
                ]
            )

        assert mock_call.await_count == 1
        assert result is not None
        assert len(result.descriptions) == 1

    asyncio.run(_run())


def test_describe_retries_only_failed_indexes_and_preserves_valid_items() -> None:
    async def _run() -> None:
        svc = LlmService(_config())
        extractor = DescribeExtractor(svc)
        first = EventDescriptionBatchResponse(
            descriptions=[
                _description(
                    0,
                    headline="Port strike disrupts terminal operations",
                    summary="Dockworkers halted 3 berths in Rotterdam on November 5.",
                ),
                _description(
                    1,
                    headline="Pipeline leak shuts refinery unit",
                    summary="Crews reported 99 barrels spilled near Houston.",
                ),
            ]
        )
        retry = EventDescriptionBatchResponse(
            descriptions=[
                _description(
                    1,
                    headline="Pipeline leak shuts refinery unit",
                    summary="Crews shut one refinery unit near Houston on November 5.",
                )
            ]
        )

        captured_prompts: list[str] = []

        async def fake_complete_json(**kwargs: object) -> EventDescriptionBatchResponse:
            prompt = str(kwargs["user_prompt"])
            captured_prompts.append(prompt)
            return first if len(captured_prompts) == 1 else retry

        items = [
            _item(0, fact="Dockworkers halted 3 berths in Rotterdam."),
            _item(1, fact="Crews shut a refinery unit near Houston after a leak."),
        ]

        with patch.object(svc, "complete_json", side_effect=fake_complete_json):
            result = await extractor.describe(items)

        assert len(captured_prompts) == 2
        assert "Port strike" not in captured_prompts[1]
        assert "refinery unit near Houston" in captured_prompts[1]
        assert result is not None
        assert [desc.index for desc in result.descriptions] == [0, 1]
        assert "3 berths" in result.descriptions[0].summary
        assert "refinery unit" in result.descriptions[1].summary

    asyncio.run(_run())


def test_describe_keeps_valid_items_if_retry_still_fails_or_errors() -> None:
    async def _run() -> None:
        svc = LlmService(_config())
        extractor = DescribeExtractor(svc)
        first = EventDescriptionBatchResponse(
            descriptions=[
                _description(
                    0,
                    headline="Port strike disrupts terminal operations",
                    summary="Dockworkers halted 3 berths in Rotterdam.",
                ),
                _description(
                    1,
                    headline="Pipeline leak shuts refinery unit",
                    summary="Crews reported 99 barrels spilled near Houston.",
                ),
            ]
        )
        items = [
            _item(0, fact="Dockworkers halted 3 berths in Rotterdam."),
            _item(1, fact="Crews shut a refinery unit near Houston after a leak."),
        ]

        with patch.object(
            svc, "complete_json", new_callable=AsyncMock, side_effect=[first, None]
        ):
            result = await extractor.describe(items)

        assert result is not None
        assert [desc.index for desc in result.descriptions] == [0]

    asyncio.run(_run())
