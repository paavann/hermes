"""Tests for PairAdjudicator article and event-merge adjudication."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from hermes_ai import (
    PAIR_ADJUDICATION_PROMPT_VERSION,
    PAIR_MERGE_PROMPT_VERSION,
    PairAdjudication,
    PairAdjudicationInput,
    PairAdjudicationResponse,
    PairAdjudicator,
    PairDecision,
    PairSide,
)
from hermes_ai.exceptions import SchemaValidationError
from hermes_ai.extractors.adjudicate import build_pair_payload


def _side(
    headline: str,
    *,
    location: str,
    category: str,
    actors: list[str] | None = None,
) -> PairSide:
    return PairSide(
        headline=headline,
        summary=f"{headline} summary.",
        entities=["Office for National Statistics"],
        actors=actors or [],
        location=location,
        occurred_at="2026-11-26T10:15:00+00:00",
        category=category,
    )


def test_build_pair_payload_includes_actors_only_when_present() -> None:
    payload = json.loads(
        build_pair_payload(
            [
                PairAdjudicationInput(
                    index=0,
                    left=_side(
                        "UK net migration falls to 77,000",
                        location="UK",
                        category="POLITICS",
                        actors=["Office for National Statistics (ORGANIZATION/ACTOR/GB)"],
                    ),
                    right=_side(
                        "International net migration 77,000 in UK",
                        location="UK",
                        category="POLITICS",
                    ),
                )
            ]
        )
    )
    assert payload[0]["left"]["actors"] == [
        "Office for National Statistics (ORGANIZATION/ACTOR/GB)"
    ]
    assert "actors" not in payload[0]["right"]


def test_decide_merge_uses_merge_v1_prompt_and_filters_unknown_indexes() -> None:
    fake_llm = MagicMock()
    fake_llm.model_for.return_value = "mistral/merge"
    fake_llm.complete_json = AsyncMock(
        return_value=PairAdjudicationResponse(
            decisions=[
                PairAdjudication(
                    index=0,
                    decision=" same ",  # type: ignore[arg-type]
                    confidence=0.94,
                ),
                PairAdjudication(
                    index=42,
                    decision=PairDecision.DIFFERENT,
                    confidence=0.9,
                ),
            ]
        )
    )

    adjudicator = PairAdjudicator(fake_llm)
    assert adjudicator.prompt_version == PAIR_ADJUDICATION_PROMPT_VERSION
    assert adjudicator.merge_prompt_version == PAIR_MERGE_PROMPT_VERSION
    assert adjudicator.merge_prompt_version == "merge-v1"

    response = asyncio.run(
        adjudicator.decide_merge(
            [
                PairAdjudicationInput(
                    index=0,
                    left=_side(
                        "Zeeshan Ali set to board China's Tiangong station",
                        location="China",
                        category="SCIENCE",
                    ),
                    right=_side(
                        "Zeeshan Ali boards China's space station",
                        location="China",
                        category="TECHNOLOGY",
                    ),
                )
            ]
        )
    )

    assert response is not None
    assert len(response.decisions) == 1
    assert response.decisions[0].decision == PairDecision.SAME
    call_kwargs = fake_llm.complete_json.await_args.kwargs
    assert call_kwargs["task"] == "adjudicate"
    assert "duplicate-event reconciliation adjudicator" in call_kwargs["sys_prompt"]


def test_decide_merge_returns_none_on_schema_error() -> None:
    fake_llm = MagicMock()
    fake_llm.complete_json = AsyncMock(side_effect=SchemaValidationError("bad json"))
    adjudicator = PairAdjudicator(fake_llm)

    response = asyncio.run(
        adjudicator.decide_merge(
            [
                PairAdjudicationInput(
                    index=0,
                    left=_side("A", location="UK", category="POLITICS"),
                    right=_side("B", location="UK", category="POLITICS"),
                )
            ]
        )
    )
    assert response is None
