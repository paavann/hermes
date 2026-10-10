# Hermes AI — AI Agent Context

## 1. Architectural Boundary & Posture
`hermes-ai` is the central library for all LLM inference, embedding generation, structured event/timeline extraction, and grounded geocoding across the Hermes platform.
- **Zero Database Dependencies**: `hermes-ai` must NEVER import anything from `hermes-db` or consumer applications (`apps/hermes-api`, `apps/hermes-worker`). It is completely database-agnostic.
- **Protocol-Driven Inversion of Control**: Caching for geocoding relies on `GeocodeCacheProtocol`. Storage adapters (such as `GeocodeCacheService` in `hermes-db`) are injected at runtime by consumer applications without tying `hermes-ai` to SQLAlchemy or PostgreSQL.
- **Pure Domain & Transport Models**: All extraction payloads (`ExtractedEvent`, `TlExtractionResponse`, `TlSearchQuery`, etc.) are defined using strict Pydantic v2 schemas.

---

## 2. Structural Layering & Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                      HermesAiClient                         │
│  (High-Level Facade: extract_events, extract_tl, triage)    │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
               ▼                               ▼
      ┌──────────────────┐           ┌──────────────────┐
      │  EventExtractor  │           │   TlExtractor    │
      └────────┬─────────┘           └─────────┬────────┘
               │                               │
               └───────────────┬───────────────┘
                               │
                               ▼
                      ┌──────────────────┐
                      │    LlmService    │
                      │  - LiteLLM Router│
                      │  - TbRateLimiter │
                      │  - Schema Failover│
                      │  - gen_embeddings│
                      └──────────────────┘
```

- **`LlmService` (`hermes_ai.services.llm`)**: Low-level engine handling LiteLLM `Router`, token-bucket rate limiting (`TbRateLimiter`), semantic fallback upon JSON `ValidationError`, and vector embeddings via `litellm.aembedding`.
- **`HermesAiClient` (`hermes_ai.client`)**: Thin facade delegating low-level calls to `LlmService` while managing domain extractors.
- **`EventExtractor` & `TlExtractor` (`hermes_ai.extractors.*`)**: Domain prompt builders and parsers. Handles article batch slicing (`ARTICLE_BATCH_SIZE = 5`), category color assignments, and Wikipedia timeline graph resolution.
- **`GeocodingService` (`hermes_ai.services.geocoding`)**: Robust OpenStreetMap Nominatim client protected by `NominatimResilienceManager` (rate-pacing, retry with exponential backoff on HTTP 429, circuit breaker) and sanitization rules (`clean_location_name`).

---

## 3. Resilience & Defense-in-Depth Mechanisms
1. **Schema Validation Fallover**: LiteLLM's native router only catches HTTP-level exceptions. When smaller parameter models return HTTP 200 with invalid schema payloads, `LlmService.call_llm` catches `ValidationError` and retries against the configured fallback model (`fallback-extractor`).
2. **Defensive Schema Prompting**: System prompts explicitly command models not to echo `$defs` schema definitions or object-wrapped values.
3. **Resilient Geoparsing**: Trailing ISO-2 country codes (e.g. `", US"`, `", IN"`) and generic composite location descriptors (`"multiple"`, `"various"`) are stripped before Nominatim queries to maximize hit rates.
