"""Tests for the ChatRetriever protocol boundary."""

import asyncio
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime

import pytest

from hermes_ai.chat.models import (
    ChatScope,
    Coverage,
    CoverageLevel,
    RetrievalFilters,
    RetrievalResult,
    RetrievedEvidence,
    ScopeType,
)
from hermes_ai.chat.retriever import ChatRetriever


class FakeRetriever:
    def __init__(self, result: RetrievalResult) -> None:
        self.result = result
        self.calls: list[tuple[str, ChatScope, RetrievalFilters | None]] = []

    async def retrieve(
        self,
        query: str,
        *,
        scope: ChatScope,
        filters: RetrievalFilters | None = None,
        recency_intent: bool = False,
    ) -> RetrievalResult:
        self.calls.append((query, scope, filters, recency_intent))
        return self.result


def _result() -> RetrievalResult:
    now = datetime.now(UTC)
    return RetrievalResult(
        evidence=[
            RetrievedEvidence(
                event_id=uuid.uuid4(),
                headline="Flooding in Valencia",
                category="DISASTER",
                impact_level="HIGH",
                status="ACTIVE",
                first_reported_at=now,
                last_updated_at=now,
            )
        ],
        coverage=Coverage(level=CoverageLevel.SUFFICIENT, result_count=1),
    )


def test_fake_retriever_conforms_to_protocol() -> None:
    fake = FakeRetriever(_result())
    retriever: ChatRetriever = fake
    scope = ChatScope(type=ScopeType.GLOBAL)
    filters = RetrievalFilters(category="DISASTER")

    async def run() -> RetrievalResult:
        return await retriever.retrieve("flooding", scope=scope, filters=filters)

    result = asyncio.run(run())

    assert result.coverage.level is CoverageLevel.SUFFICIENT
    assert fake.calls == [("flooding", scope, filters, False)]


def test_retrieval_filters_reject_reversed_range() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValueError, match="start must be before"):
        RetrievalFilters(start=now, end=now.replace(year=now.year - 1))


def test_chat_retriever_module_does_not_import_hermes_db() -> None:
    code = """
import sys
import hermes_ai.chat.retriever

assert "hermes_db" not in sys.modules, sorted(
    name for name in sys.modules if name.startswith("hermes_db")
)
print("database-free")
"""
    env = os.environ.copy()
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "database-free" in result.stdout
