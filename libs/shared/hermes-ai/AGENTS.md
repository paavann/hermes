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
- **Client Facade Entry Point**: External consumers (`apps/hermes-api`, `apps/hermes-worker`) must interact via `HermesAiClient`, never directly with `LlmService` or individual extractors.
- **Location Text Only**: The LLM must never supply latitude or longitude coordinates; it returns cleaned location names only.
- **Geocoding Resilience**: Never bypass the token-bucket rate limiter (`NominatimResilienceManager`), in-flight request deduplication, or circuit breaker.
- **Negative Caching**: A cache record with null coordinates represents a confirmed unlocatable entity. Never treat it as a cache miss or retry it against Nominatim.
- **Schema-Level Failover**: `LlmService` intercepts Pydantic `ValidationError` on malformed HTTP 200 model outputs and automatically dispatches to the configured fallback extractor.

## 3. Tunables

- Batch size: `ARTICLE_BATCH_SIZE` in `libs/shared/hermes-ai/src/hermes_ai/core/constants.py`

## 4. Domain Triggers

- **When modifying model routing, failover mechanisms, or geocoding architecture**: Read `libs/shared/hermes-ai/docs/architecture.md`.
