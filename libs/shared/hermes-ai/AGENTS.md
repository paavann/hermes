# Hermes AI (`libs/shared/hermes-ai`)

Shared geospatial and conversational RAG intelligence library providing LLM extraction, grounded Nominatim geocoding, vector embeddings, and citation-backed chat orchestration. Run all Nx commands from the workspace root using project `hermes-ai`.

## 2. Invariants

- **Zero Database Coupling**: Never import `hermes-db` or ORM models. All caching contracts are mediated via `GeocodeCacheProtocol`; consumers inject concrete cache implementations at runtime.
- **Client Facade Entry Point**: External consumers (`apps/hermes-api`, `apps/hermes-worker`) must interact via `HermesAi`, never directly with `LlmService` or individual extractors.
- **Explicit Config Injection**: Never read `.env` or `os.environ` inside `src/hermes_ai/`. Consumer apps resolve API keys, model names, and Langfuse settings and pass them explicitly into `HermesAi(...)`.
- **Location Text Only**: The LLM must never supply latitude or longitude coordinates; it returns cleaned location names only.
- **Geocoding Resilience**: Never bypass the token-bucket rate limiter (`NominatimResilienceManager`), in-flight request deduplication, or circuit breaker.
- **Negative Caching**: A cache record with null coordinates represents a confirmed unlocatable entity. Never treat it as a cache miss or retry it against Nominatim.
- **Schema-Level Failover**: `LlmService` intercepts Pydantic `ValidationError` on malformed HTTP 200 model outputs and automatically dispatches to the configured fallback extractor.
- **Tracing Singleton Lifecycle**: `LlmService` manages the Langfuse SDK singleton. It is initialized on `__init__` when `tracing_enabled=True` and `langfuse_public_key`/`langfuse_secret_key` are provided. Consumers must invoke `aclose()` during process/task teardown to flush pending telemetry.
- **Tracing is Opt-In & Privacy-Guarded**: Never assume tracing is active. The absence of Langfuse credentials must be a clean no-op. All extractor `@observe` decorators (`event-extract`, `tl-extract`, `tl-analyze`) must enforce `capture_input=False, capture_output=False` to prevent leaking raw article texts or prompt content into telemetry stores.
- **Chat Engine & Import Isolation**: Keep `hermes_ai/chat/` (planner, retriever, citation stream) decoupled from `hermes-db` ORM models and FastAPI HTTP types; preserve import isolation verified by `tests/test_import_isolation.py`.

## 3. Domain Triggers (Code Modifications Only)

- **When modifying model routing, failover, or geocoding resilience**: Read `libs/shared/hermes-ai/README.md`.
- **When modifying Langfuse tracing or `@observe` decorators**: Inspect `src/hermes_ai/services/langfuse.py` and `src/hermes_ai/utils/tracing.py`.
