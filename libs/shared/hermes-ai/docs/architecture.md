# Hermes AI — Architecture & Design Rationale

> [!NOTE]
> This is human-readable design documentation. It is not auto-loaded into agent context during standard sessions. Consult this document when modifying LLM model routing, extraction schemas, Nominatim geocoding policies, or vector embedding configurations.

---

## 1. Architectural Boundaries & Posture

`hermes-ai` is the shared geospatial intelligence library for Project Hermes. It provides unified LLM orchestration, structured news/timeline extraction, grounded OpenStreetMap geocoding, and vector embeddings for `apps/hermes-api` and `apps/hermes-worker`.

- **Zero Database Coupling**: `hermes-ai` has zero dependencies on `hermes-db` or PostgreSQL ORM models. All caching contracts are mediated via `GeocodeCacheProtocol` (Inversion of Control). Storage implementations (`GeocodeCacheService`) are injected at runtime by consumer applications.
- **Pure Domain Schemas**: All data exchanges utilize strict Pydantic v2 domain schemas (`ExtractedEvent`, `ExtractionResponse`, `GroundedEvent`, `TlExtractionResponse`, `TlSearchQuery`).
- **Defensive Extraction Facade**: Consumer applications interact primarily via `HermesAiClient`, which orchestrates low-level model routing, rate-limiting, and domain extractors (`EventExtractor`, `TlExtractor`).

```text
┌─────────────────────────────────────────────────────────────┐
│                      HermesAiClient                         │
│   (Facade: extract_events, extract_tl, gen_embeddings)      │
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
                      ┌──────────────────┐      ┌─────────────────────────┐
                      │    LlmService    │      │    GeocodingService     │
                      │  - LiteLLM Router│      │  - OSM Nominatim Pacing │
                      │  - TbRateLimiter │◄────►│  - In-Flight Dedup      │
                      │  - Two-Tier Fail │      │  - Negative Cache Check │
                      │  - gen_embeddings│      │  - Circuit Breaker      │
                      └──────────────────┘      └─────────────────────────┘
```

---

## 2. Engineering Decisions & Tradeoffs ("The Why")

### 1. LiteLLM Abstraction for Model Decoupling
- **The Why**: Proprietary SDKs create tight vendor lock-in. LiteLLM abstracts diverse inference APIs (Mistral, NVIDIA NIM, OpenAI, Anthropic) under a standardized client interface (`Router`), unifying structured outputs (`response_format={"type": "json_schema"}`) and async completions.
- **Tradeoff**: LiteLLM adds an abstraction layer, but eliminates model migration friction and centralizes retry/cooldown parameters across worker and API tiers.

### 2. Dual-Tier Failover & Polymorphic Schema Ingestion
- **The Why**: Small or quantized open-source models frequently output raw JSON arrays (`[...]`) instead of object envelopes (`{"events": [...]}`), embed markdown fences, or return HTTP 200 with syntactically malformed fields.
- **Mechanisms**:
  - `ExtractionResponse.wrap_raw_list`: Polymorphic `@model_validator(mode="before")` coerces raw JSON lists directly into structured event envelopes.
  - `coerce_to_str`: Defensive string coercion extracts strings from nested dicts (e.g., `{"en": "..."}`) or lists returned by errant models.
  - `_clean_json_str`: Strips markdown fences before JSON decoding.
  - **Schema-Level Failover**: Native LiteLLM routing only catches HTTP-level errors. When a primary model returns HTTP 200 with invalid schema payloads, `LlmService.call_llm` intercepts `pydantic.ValidationError` and immediately dispatches the request to the configured fallback model (`fallback-extractor`).

### 3. Dense Vector Embeddings & Database Synergy
- **The Why**: Cross-source news deduplication and source-consensus ranking require dense semantic representation across diverse multilingual feeds. Dense vector models provide high retrieval precision for news clustering.
- **Database Synergy**: In `hermes-db`, vectors are indexed via PostgreSQL + `pgvector` utilizing `halfvec` with HNSW cosine indexes (`halfvec_cosine_ops`), cutting storage and memory bandwidth by 50% while preserving high recall.

### 4. Nominatim Geocoding Shield (Compliance & Resilience)
OpenStreetMap Nominatim is a shared community resource with strict operational policies. Direct, unthrottled LLM geocoding leads to IP bans.
- **1.0s Token-Bucket Rate Limiter (`asyncio.Lock`)**: OSM Acceptable Use Policy strictly limits clients to a maximum of 1 request per second. `NominatimResilienceManager` enforces a hard `min_request_interval = 1.0s` across all async tasks using an asynchronous lock.
- **In-Flight Request Deduplication**: If multiple concurrent articles reference the same location within a batch, `_in_flight` futures ensure only a single HTTP request is sent; other coroutines await the active future.
- **Negative Caching (`_NOT_FOUND`)**: Unresolvable places (e.g., fictional regions, non-physical entities) would otherwise trigger repeated external lookups on every RSS sync cycle. Storing negative cache entries (`latitude=None, longitude=None`) in `geocode_cache` permanently eliminates redundant external queries.
- **Circuit Breaker on 429/403**: When rate-limited (HTTP 429) or blocked (HTTP 403), exponential backoff honors `Retry-After`. If 429 persists across 3 attempts, the circuit breaker trips for a cooldown period, failing fast to prevent persistent blacklisting.
- **Sanitization Shield**: `clean_location_name` strips parenthetical examples, trailing ISO country codes (e.g., `", US"`), and filters unlocatable tokens (`"multiple locations"`, `"worldwide"`) before hitting the network.

### 5. Article Batch Sizing
- **The Why**: Slicing article ingestion into bounded batches balances LLM context limits against inference latency and API call overhead. Larger batches increase hallucination rates in index mapping, while single-article calls bottleneck ingestion throughput.
