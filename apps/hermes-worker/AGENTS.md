# Hermes Worker — AI Agent Context & Engineering Rationale

`hermes-worker` is the autonomous, headless ingestion and lifecycle engine for Project Hermes. It fetches global RSS feeds, computes semantic embeddings, deduplicates events via PostGIS vector search, extracts tactical metadata via LLMs, resolves grounded coordinates through a rate-limited geocoding shield, and decays event scores over time.

---

## 1. 12-Factor Ephemeral Architecture ("The Why")

- **Why Run-and-Die vs. In-Process Schedulers (APScheduler / Celery)**:
  Long-lived worker daemons with internal cron loops suffer from memory bloat during heavy XML parsing, risk dangling coroutines, and create concurrency collisions across container restarts. Running as a stateless 12-factor CLI command (`hermes-worker run-all`) guarantees that memory is fully reclaimed upon process exit, database pools cleanly disconnect, and scheduling concerns remain strictly external.
- **Production Cloud Orchestration**:
  In production, the worker runs as a serverless container on **AWS ECS Fargate** (`0.25 vCPU`, `512 MiB`, public subnet for outbound egress). It is triggered 3x daily by an **Amazon EventBridge** schedule (`cron(0 0,8,16 * * ? *)`).
  - **Zero Idle Billing**: Running for ~3 minutes three times a day costs less than $0.05/month, compared to paying 24/7 for an idle VM or background worker container.
  - **API Isolation**: Isolates memory-heavy RSS parsing and token-heavy LLM calls entirely from `apps/hermes-api`, ensuring zero event-loop starvation for real-time map users.

---

## 2. Ingestion Pipeline Decisions & Constraints

The pipeline stage order in `services/sync.py` is strictly engineered around cost, token limits, and speed:

1. **Embed BEFORE Extract (Vector Pre-Filtering)**:
   - Computing dense 2048-dim embeddings (`nemotron-3-embed-1b`) and executing a PostGIS `pgvector` HNSW cosine distance search (`distance < 0.25`) is orders of magnitude cheaper and faster than prompting an LLM to compare raw text.
   - Candidate active events matching the cosine threshold are retrieved from the database *first* and passed into the LLM prompt. The LLM only evaluates existing candidate IDs or proposes a new event, eliminating all-pairs $O(N^2)$ LLM token consumption.
2. **Strict Batch Sizing (`ARTICLE_BATCH_SIZE = 10`)**:
   - Slicing articles into batches of 10 balances LLM context limits against inference latency and API rate limits. Single-article prompts multiply network round-trips and exhaust RPM quotas; batches larger than 10 degrade LLM extraction accuracy and trigger index-mapping hallucinations.
3. **Source Credibility & Consensus Scoring**:
   - Matching articles increment the parent event's `article_count` and add credibility weights (`TIER_1` = +3.0 down to `TIER_4` = +0.5). If a matched event was previously marked `STALE`, it is automatically reactivated to `ACTIVE`.

---

## 3. The Geocoding Shield (OSM Nominatim)

LLMs notoriously hallucinate latitude and longitude coordinates. The LLM is restricted to extracting plain-text location strings (`location_name`), which are grounded through OpenStreetMap Nominatim:

- **1.0-Second Lock (`asyncio.Lock`)**: OpenStreetMap's Acceptable Use Policy strictly mandates a maximum of 1 request per second. `NominatimResilienceManager` enforces this via an asynchronous lock across all worker tasks.
- **In-Flight Deduplication**: Concurrent articles within a batch referencing the same location share an in-flight `asyncio.Future`, guaranteeing only a single HTTP request hits the network.
- **Negative Caching (`_NOT_FOUND`)**: Unlocatable strings (e.g., "global markets", "cyberspace") are permanently persisted in `geocode_cache` with `latitude = NULL` and `longitude = NULL`. This prevents redundant outbound network calls across future sync cycles.
- **Circuit Breaker**: If HTTP 429 (Too Many Requests) persists across 3 retries, the circuit breaker trips for a 120-second cooldown, failing fast to avoid permanent IP blacklisting.

---

## 4. Lifecycle Decay & Clean Resource Teardown

- **Organic Score Decay**:
  The `run-lifecycle` command reduces all `ACTIVE` event trending scores by 10% (`trending_score * 0.9`) and transitions events past their cutoff thresholds (`ACTIVE` &rarr; `STALE` after 24h, `STALE` &rarr; `ARCHIVED` after 48h).
- **Graceful Async Database Pool Shutdown**:
  Every CLI command executes inside the `db_lifespan()` async context manager (`core/lifespan.py`). On entry, `init_db(settings.db_url)` initializes the SQLAlchemy `AsyncEngine` pool (enforcing SSL for remote hosts). In the `finally` block, `close_db()` calls `await engine.dispose()`, cleanly terminating all open socket connections to Neon PostgreSQL before process exit (`sys.exit()`).
