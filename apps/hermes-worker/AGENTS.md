# Hermes Worker — AI Agent Context

## 1. 12-Factor Ephemeral Design Rationale
`hermes-worker` deliberately avoids in-process schedulers like APScheduler. By remaining a stateless, run-and-die CLI tool, it prevents memory bloat during massive RSS ingestion and allows external orchestrators to horizontally scale or reliably retry failed pipeline executions without starving the REST API.

## 2. Pipeline Execution Constraints
The ingestion pipeline ordering is highly intentional:
- **Embed BEFORE Extract**: We generate 2048-dim vectors first, because PostGIS cosine similarity search (`< 0.25`) is dramatically cheaper and faster than asking an LLM to deduplicate raw text. The LLM is only invoked *after* candidate events are retrieved.
- **Batching**: Articles are sent to the LLM in strict batches of 10 (`ARTICLE_BATCH_SIZE`) to maximize token throughput and minimize latency while avoiding context-window overflow.

## 3. The Geocoding Shield
LLMs hallucinate coordinates. To prevent this, the LLM only extracts location strings (e.g., "Geneva, Switzerland"), which are resolved via `GeocodingService` (Nominatim).
- **1-Second Lock**: OpenStreetMap strictly requires a 1s delay between requests. This is enforced via an `asyncio.Lock()` across the worker.
- **Negative Caching**: Locations that Nominatim cannot resolve are permanently cached as `NULL` coordinates. This prevents the worker from repeatedly hammering the API for un-geocodable phrases like "global markets".
- **Circuit Breaker**: If 429/403 errors persist, the worker stops geocoding entirely for up to 60s to prevent permanent IP bans.
