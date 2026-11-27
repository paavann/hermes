"""Tests for RelationshipExtractor and relationship Pydantic schemas."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from hermes_ai import (
    RELATIONSHIP_PROMPT_VERSION,
    AiConfig,
    HermesAi,
    ModelRoute,
    ModelTarget,
    RelationshipBatchResponse,
    RelationshipDecision,
    RelationshipDirection,
    RelationshipEvalInput,
    RelationshipEventSide,
    RelationshipExtractor,
    RelationshipKind,
)
from hermes_ai.exceptions import SchemaValidationError
from hermes_ai.extractors.relationship import build_relationship_payload


def _side(
    headline: str,
    location: str,
    country: str,
    category: str,
    actors: list[str] | None = None,
) -> RelationshipEventSide:
    return RelationshipEventSide(
        headline=headline,
        summary=f"{headline} summary.",
        entities=["Zeeshan Ali", "China"],
        actors=actors or [],
        location=location,
        country_code=country,
        occurred_at="2026-11-25T08:11:00+00:00",
        category=category,
    )


def test_relationship_decision_normalizes_enums_and_clamps_rationale() -> None:
    decision = RelationshipDecision(
        index=0,
        relationship=" follow-up ",  # type: ignore[arg-type]
        direction="right to left",  # type: ignore[arg-type]
        confidence=0.92,
        rationale="  Embassy   threat   escalated into an order.  " + ("x" * 240),
    )

    assert decision.relationship == RelationshipKind.FOLLOW_UP
    assert decision.direction == RelationshipDirection.RIGHT_TO_LEFT
    assert len(decision.rationale) == 240
    assert not decision.rationale.startswith(" ")


def test_relationship_decision_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValidationError):
        RelationshipDecision(
            index=0,
            relationship=RelationshipKind.CAUSED,
            confidence=1.2,
        )


def test_build_relationship_payload_compacts_fields() -> None:
    payload = build_relationship_payload(
        [
            RelationshipEvalInput(
                index=0,
                left=_side("Boards Tiangong", "Beijing, China", "CN", "SCIENCE"),
                right=_side("SUPARCO watch party", "Islamabad, Pakistan", "PK", "TECHNOLOGY"),
            )
        ]
    )
    decoded = json.loads(payload)
    assert decoded[0]["index"] == 0
    assert decoded[0]["left"]["country_code"] == "CN"
    assert decoded[0]["right"]["location"] == "Islamabad, Pakistan"
    assert "actors" not in decoded[0]["left"]

    actor_payload = json.loads(
        build_relationship_payload(
            [
                RelationshipEvalInput(
                    index=0,
                    left=_side(
                        "Israeli strikes in Gaza",
                        "Gaza Strip",
                        "PS",
                        "CONFLICT",
                        actors=["Israel (STATE/ACTOR/IL)"],
                    ),
                    right=_side(
                        "Israel institutionalises torture report",
                        "Israel",
                        "IL",
                        "POLITICS",
                        actors=["Israel (STATE/ACTOR/IL)"],
                    ),
                )
            ]
        )
    )
    assert actor_payload[0]["left"]["actors"] == ["Israel (STATE/ACTOR/IL)"]
    assert RELATIONSHIP_PROMPT_VERSION == "relation-v2"


def test_extractor_filters_unknown_indexes_and_wires_client() -> None:
    ai = HermesAi(
        AiConfig(
            routes={
                "extractor": ModelRoute(
                    primary=ModelTarget(model="mistral/test", api_key="key")
                ),
                "relationship": ModelRoute(
                    primary=ModelTarget(model="mistral/rel", api_key="rel-key")
                ),
            }
        )
    )
    assert isinstance(ai.relationships, RelationshipExtractor)
    assert ai.relationships.model_name == "mistral/rel"

    fake_llm = MagicMock()
    fake_llm.model_for.return_value = "mistral/rel"
    fake_llm.complete_json = AsyncMock(
        return_value=RelationshipBatchResponse(
            decisions=[
                RelationshipDecision(
                    index=0,
                    relationship=RelationshipKind.REACTION,
                    direction=RelationshipDirection.LEFT_TO_RIGHT,
                    confidence=0.93,
                    rationale="Islamabad students watched Zeeshan Ali board Tiangong.",
                ),
                RelationshipDecision(
                    index=99,
                    relationship=RelationshipKind.NONE,
                    confidence=0.8,
                ),
            ]
        )
    )

    extractor = RelationshipExtractor(fake_llm)
    response = asyncio.run(
        extractor.classify(
            [
                RelationshipEvalInput(
                    index=0,
                    left=_side("Boards Tiangong", "Beijing, China", "CN", "SCIENCE"),
                    right=_side("SUPARCO watch party", "Islamabad, Pakistan", "PK", "TECHNOLOGY"),
                )
            ]
        )
    )

    assert response is not None
    assert len(response.decisions) == 1
    assert response.decisions[0].relationship == RelationshipKind.REACTION
    assert fake_llm.complete_json.await_args.kwargs["task"] == "relationship"


def test_extractor_returns_none_on_schema_error() -> None:
    fake_llm = MagicMock()
    fake_llm.complete_json = AsyncMock(side_effect=SchemaValidationError("bad json"))
    extractor = RelationshipExtractor(fake_llm)

    result = asyncio.run(
        extractor.classify(
            [
                RelationshipEvalInput(
                    index=0,
                    left=_side("A", "Pyongyang", "KP", "POLITICS"),
                    right=_side("B", "Pyongyang", "KP", "CONFLICT"),
                )
            ]
        )
    )
    assert result is None
