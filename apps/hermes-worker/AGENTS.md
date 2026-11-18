# Hermes Worker

Autonomous, run-and-die batch CLI for news ingestion, event construction, geocoding, and lifecycle maintenance. Executes one command per process; never runs as a persistent daemon.

## 1. Commands

Execute from the workspace root (see root `AGENTS.md` for lint, format, and test commands):

| Task               | Command                                     | Description                                                                     |
| :----------------- | :------------------------------------------ | :------------------------------------------------------------------------------ |
| **Ingest Articles**| `npx nx run hermes-worker:ingest-articles`  | Sync the source registry, fetch due feeds, and write the deduplicated ledger     |
| **Audit Sources**  | `npx nx run hermes-worker:audit-sources`    | Probe configured feeds and sample articles read-only                            |
| **Maintain Events**| `npx nx run hermes-worker:maintain-events`  | Requeue abandoned article claims and apply score decay / status transitions      |
| **Healthcheck**    | `npx nx run hermes-worker:healthcheck`      | Check database connectivity, schema, queue depth, and stale claims               |
| **Reset DB**       | `npx nx run hermes-worker:reset-db`         | Drop local database objects only; guarded by `--yes` and a local-target check    |

`build-events` is added in its implementation phase. Do not reintroduce a `pipeline-*` command or a feature flag that shadows a real command.

## 2. Boundaries

- **Execution Approval**: `ingest-articles` and `maintain-events` mutate the database. Never execute them without explicit user approval (and verify `DB_HOST` in `.env` first per root `AGENTS.md`).
- **Read-Only Probe**: `healthcheck` and `audit-sources` must not write rows. `healthcheck` may be run during an incident without approval; `audit-sources` performs outbound network probes but never writes the database or the source config.
- **Network Isolation in Tests**: All tests in `tests/` are mocked. Never write tests that hit the network, call external APIs, or query a live database. Database tests use the `integration` marker and skip without `TEST_DATABASE_URL`.

## 3. Invariants

- **Connection Lifespan**: Every database-backed CLI handler must execute inside `db_lifespan()` (`core/lifespan.py`) to guarantee connection disposal on exit. `audit-sources` is network-only and intentionally runs without a database session.
- **One Command, One Job**: Commands live in `jobs/commands.py`; stage order and locking live there, not in handlers. Handlers only translate CLI arguments.
- **Stage Contract**: Every stage implements `jobs.context.Stage`, receives a `JobContext`, returns `StageStats`, and owns its transaction boundary. Domain services never commit.
- **Claim-Based Work**: Stages claim articles via `ArticleQueue` (`FOR UPDATE SKIP LOCKED`) rather than scanning and mutating rows in place. The queue never commits.
- **Ledger Identity**: Every ingested row stores `canonical_url` and `canonical_url_hash`. Ingest inserts with `ON CONFLICT DO NOTHING`; it never updates or revives an existing article row. `duplicate_of_id` is set only by explicit reconciliation.
- **Source Config Ownership**: `sources.json` owns feed URLs, provider, fallback, paywall, and fetch policy. The ingest stage syncs and commits those fields; other commands never sync sources.
- **Bounded LLM Spend**: Reserve calls through `JobContext.budget` before invoking `complete_json`; exceeding `MAX_LLM_CALLS_PER_RUN` must fail the stage, not run unbounded.
- **No Run Telemetry Table**: The process exit code and structured logs are the execution record. Article claim fields (`claimed_at`, `claimed_by`, `attempt_count`, `last_error`) are the durable work state. Do not add a run-telemetry table without a concrete query that cannot be served by logs or domain rows.
- **Telemetry Flush on Exit**: Ensure `LlmService.aclose()` -> `get_client().flush()` executes on process exit so buffered Langfuse telemetry flushes before ephemeral Fargate container teardown.
- **Failure Exit**: Exit with a non-zero status code (`sys.exit(1)`) on unhandled exceptions or execution failures.

## 4. Runtime & Memory

The worker runs in production as a scheduled AWS Fargate task (0.25 vCPU, 512 MB RAM, ephemeral one-shot container) with no state between invocations. Process feeds in bounded batches using the concurrency semaphore and the `ARTICLE_*` limits; never accumulate all feeds or articles in memory. For container entrypoints and deployment configuration, inspect `apps/hermes-worker/Dockerfile` and `.github/workflows/cd-worker.yml`.

## 5. Tunables

Changing any of these requires explaining the expected effect and obtaining approval:

- Claim queue: `ARTICLE_CLAIM_BATCH_SIZE`, `ARTICLE_CLAIM_STALE_MINUTES`, `ARTICLE_MAX_ATTEMPTS` in `apps/hermes-worker/src/hermes_worker/core/config.py`
- Ingest window: `ARTICLE_MAX_AGE_HOURS`, `ARTICLE_FUTURE_SKEW_HOURS`, `SOURCE_FETCH_CONCURRENCY` in `apps/hermes-worker/src/hermes_worker/core/config.py`
- Lifecycle cutoffs: `DEFAULT_EVENT_STALE_HRS` and `DEFAULT_EVENT_ARCHIVE_HRS` in `libs/shared/hermes-db/src/hermes_db/services/event.py`; `EVENT_STALE_HOURS` and `EVENT_ARCHIVE_HOURS` in `apps/hermes-worker/src/hermes_worker/core/config.py`
- Per-run LLM budget: `MAX_LLM_CALLS_PER_RUN` in `apps/hermes-worker/src/hermes_worker/core/config.py`

## 6. Triggers (Code Modifications Only)

- **When modifying stage order, claim semantics, thresholds, decay, or scheduling**: Read `apps/hermes-worker/docs/architecture.md`.
- **When modifying geocoding logic, rate limits, or caches**: Read `libs/shared/hermes-ai/AGENTS.md`.
