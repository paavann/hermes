# Hermes AI (`libs/shared/hermes-ai`)

Shared geospatial intelligence library providing LLM extraction, grounded Nominatim geocoding, and vector embeddings.

## 1. Commands

Run commands from the workspace root using project `hermes-ai`. See root `AGENTS.md` Commands table for syntax.

| Task     | Command                 |
| :------- | :---------------------- |
| **Lint** | `npx nx lint hermes-ai` |
| **Test** | `npx nx test hermes-ai` |

## 2. Invariants

- **Zero Database Coupling**: Never import `hermes-db` or ORM models. All caching contracts are mediated via `GeocodeCacheProtocol`; consumers inject concrete cache implementations at runtime.
- **Client Facade Entry Point**: External consumers (`apps/hermes-api`, `apps/hermes-worker`) must interact via `HermesAi`, never directly with `LlmService` or individual extractors.
- **Location Text Only**: The LLM must never supply latitude or longitude coordinates; it returns cleaned location names only.
- **Geocoding Resilience**: Never bypass the token-bucket rate limiter (`NominatimResilienceManager`), in-flight request deduplication, or circuit breaker.
- **Negative Caching**: A cache record with null coordinates represents a confirmed unlocatable entity. Never treat it as a cache miss or retry it against Nominatim.
- **Schema-Level Failover**: `LlmService` intercepts Pydantic `ValidationError` on malformed HTTP 200 model outputs and automatically dispatches to the configured fallback extractor.
- **Tracing Singleton Lifecycle**: `LlmService` manages the Langfuse SDK singleton. It is initialized on `__init__` when `tracing_enabled=True` and `langfuse_public_key`/`langfuse_secret_key` are provided. Consumers must invoke `aclose()` during process/task teardown to flush pending telemetry.
- **Tracing is Opt-In & Privacy-Guarded**: Never assume tracing is active. The absence of Langfuse credentials must be a clean no-op. All extractor `@observe` decorators (`event-extract`, `tl-extract`, `tl-analyze`) must enforce `capture_input=False, capture_output=False` to prevent leaking raw article texts or prompt content into telemetry stores.

## 3. Tunables

- Batch size: `ARTICLE_BATCH_SIZE` in `libs/shared/hermes-ai/src/hermes_ai/core/constants.py`

## 4. Domain Triggers

- **When modifying model routing, failover mechanisms, or geocoding architecture**: Read `libs/shared/hermes-ai/docs/architecture.md`.
- **When modifying tracing, `@observe` decorators, or Langfuse SDK initialization**: Inspect `libs/shared/hermes-ai/src/hermes_ai/services/llm.py` and ensure `LlmService.aclose()` flush calls and privacy protections (`capture_input=False, capture_output=False`) are preserved.
