# Hermes Worker

Autonomous, run-and-die batch CLI for news ingestion, vector deduplication, geocoding, and score decay. Executes one command per process; never runs as a persistent daemon.

## 1. Commands

Execute from the workspace root (see root `AGENTS.md` for lint, format, and test commands):

| Task               | Command                                  | Description                                                             |
| :----------------- | :--------------------------------------- | :---------------------------------------------------------------------- |
| **Run All**        | `npx nx run hermes-worker:run-all`       | Lifecycle decay followed by source sync                                 |
| **Sync Only**      | `npx nx run hermes-worker:run-sync`      | Ingest due RSS feeds (`uv run hermes-worker run-sync --force` to force) |
| **Lifecycle Only** | `npx nx run hermes-worker:run-lifecycle` | Apply score decay & status transitions                                  |

## 2. Boundaries

- **Pipeline Execution Approval**: `run-all` and `run-sync` consume LLM tokens, query Nominatim, and mutate the database. Never execute them without explicit user approval (and verify `DB_HOST` in `.env` first per root `AGENTS.md`).
- **Network Isolation in Tests**: All tests in `tests/` are 100% mocked. Never write tests that hit the network, call external APIs, or query a live database.

## 3. Invariants

- **Connection Lifespan**: Every CLI handler must execute inside `db_lifespan()` (`core/lifespan.py`) to guarantee connection disposal on exit.
- **Pipeline Stage Order**: Maintain sequence in `services/sync.py`: compute embeddings, query candidate events via PostGIS HNSW cosine distance, then pass candidates to the LLM to confirm or create an event. Never send articles to an LLM for pairwise comparison.
- **Lifecycle Transitions**: Events progress `ACTIVE -> STALE -> ARCHIVED` by age. A matched incoming article reactivates a `STALE` event to `ACTIVE`.
- **Telemetry Flush on Exit**: Ensure `LlmService.aclose()` -> `get_client().flush()` executes on process exit so buffered Langfuse telemetry flushes before ephemeral Fargate container teardown.
- **Failure Exit**: Exit with a non-zero status code (`sys.exit(1)`) on unhandled exceptions or execution failures.

## 4. Runtime & Memory

The worker runs in production as a scheduled AWS Fargate task (0.25 vCPU, 512 MB RAM, ephemeral one-shot container) with no state between invocations. Process feeds in bounded batches using the concurrency semaphore and `ARTICLE_BATCH_SIZE`; never accumulate all feeds or articles in memory. For container entrypoints and deployment configuration, inspect `apps/hermes-worker/Dockerfile` and `.github/workflows/cd-worker.yml`.

## 5. Tunables

These parameters interact without test validation; changing any requires explaining the expected effect and obtaining approval:

- Batch size: `ARTICLE_BATCH_SIZE` in `libs/shared/hermes-ai/src/hermes_ai/core/constants.py`
- Similarity threshold: Cosine distance literal in `libs/shared/hermes-db/src/hermes_db/services/event.py`
- Credibility & decay: `CREDIBILITY_WEIGHTS` and `HOURLY_DECAY_FACTOR` in `libs/shared/hermes-db/src/hermes_db/services/ranking.py`
- Lifecycle cutoffs: `DEFAULT_EVENT_STALE_HRS` and `DEFAULT_EVENT_ARCHIVE_HRS` in `libs/shared/hermes-db/src/hermes_db/services/event.py`; `EVENT_STALE_HOURS` and `EVENT_ARCHIVE_HOURS` in `apps/hermes-worker/src/hermes_worker/core/config.py`
- Vector dimensions & models: `HALFVEC` dimension in `libs/shared/hermes-db/src/hermes_db/models/event.py`; `LLM_MODEL` and `EMBED_MODEL` in `apps/hermes-worker/src/hermes_worker/core/config.py`

## 6. Triggers (Code Modifications Only)

- **When modifying pipeline order, batching, thresholds, decay, or scheduling**: Read `apps/hermes-worker/docs/architecture.md`.
- **When modifying geocoding logic, rate limits, or caches**: Read `libs/shared/hermes-ai/AGENTS.md`.
