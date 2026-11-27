from __future__ import annotations
import enum
import logging
import os
import socket
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Protocol
from hermes_ai import GeocodingService, HermesAi
from hermes_db.services import GeocodeCacheService
from hermes_db.session import AsyncSessionLocal, get_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from hermes_worker.core.ai import create_ai_client
from hermes_worker.core.config import Settings
from hermes_worker.jobs.errors import BudgetExhaustedError, JobError


logger = logging.getLogger(__name__)


class StageName(enum.StrEnum):
    INGEST = "ingest"
    ANALYZE = "analyze"
    CLUSTER = "cluster"
    DESCRIBE = "describe"
    SCORE = "score"
    THREAD = "thread"
    RECONCILE = "reconcile"
    RELATIONSHIP = "relationship"
    REQUEUE_CLAIMS = "requeue-claims"
    REQUEUE_ARTICLES = "requeue-articles"
    EVENT_LIFECYCLE = "event-lifecycle"
    THREAD_LIFECYCLE = "thread-lifecycle"
    MAINTENANCE = "maintenance"
    HEALTHCHECK = "healthcheck"


class StageOutcome(enum.StrEnum):
    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"


@dataclass(slots=True)
class StageStats:
    counters: dict[str, int] = field(default_factory=dict)

    def add(self, name: str, amount: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + amount


@dataclass(slots=True)
class LlmBudget:
    max_llm_calls: int
    used_llm_calls: int = 0

    @property
    def remaining_llm_calls(self) -> int:
        return max(0, self.max_llm_calls - self.used_llm_calls)

    def reserve_llm_calls(self, count: int = 1) -> None:
        if count <= 0:
            raise ValueError("llm call reservation must be positive.")
        if self.used_llm_calls + count > self.max_llm_calls:
            raise BudgetExhaustedError(
                f"llm call budget exhausted: {self.used_llm_calls} of "
                f"{self.max_llm_calls} used."
            )
        self.used_llm_calls += count


@dataclass(frozen=True, slots=True)
class WorkerIdentity:
    hostname: str
    pid: int

    @property
    def id(self) -> str:
        return f"{self.hostname}:{self.pid}"[:128]


def build_worker_identity() -> WorkerIdentity:
    return WorkerIdentity(hostname=socket.gethostname(), pid=os.getpid())


@dataclass(slots=True)
class JobContext:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    identity: WorkerIdentity
    budget: LlmBudget
    ai: HermesAi | None = None
    geocoder: GeocodingService | None = None
    geocode_session: AsyncSession | None = None
    _telemetry_flushed: bool = False

    def require_ai(self) -> HermesAi:
        if self.ai is None:
            raise JobError("job context was created without an ai client.")
        return self.ai

    def require_geocoder(self) -> GeocodingService:
        if self.geocoder is None:
            raise JobError("job context was created without a geocoding service.")
        return self.geocoder

    async def flush_telemetry(self) -> None:
        if self._telemetry_flushed or self.ai is None:
            return
        self._telemetry_flushed = True
        try:
            await self.ai.aclose()
        except Exception as exc:
            logger.warning("failed to flush telemetry: %s.", exc)

    async def aclose(self) -> None:
        await self.flush_telemetry()
        if self.geocode_session is not None:
            await self.geocode_session.close()
            self.geocode_session = None


class Stage(Protocol):
    name: StageName

    async def run(self, ctx: JobContext) -> StageStats: ...


@asynccontextmanager
async def create_job_context(
    settings: Settings,
    *,
    with_ai: bool = False,
    with_geocoder: bool = False,
) -> AsyncGenerator[JobContext]:
    ctx = JobContext(
        settings=settings,
        engine=get_engine(),
        session_factory=AsyncSessionLocal,
        identity=build_worker_identity(),
        budget=LlmBudget(max_llm_calls=settings.MAX_LLM_CALLS_PER_RUN),
    )

    try:
        if with_ai:
            ctx.ai = create_ai_client(settings)
        if with_geocoder:
            session = AsyncSessionLocal()
            ctx.geocode_session = session
            ctx.geocoder = GeocodingService(
                cache_service=GeocodeCacheService(session),
                user_agent=settings.NOMINATIM_USER_AGENT,
            )
        yield ctx
    finally:
        await ctx.aclose()
