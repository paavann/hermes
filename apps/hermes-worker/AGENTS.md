# Hermes Worker

Autonomous, run-and-die batch CLI for news ingestion, event construction, geocoding, and lifecycle maintenance. Executes one command per process; never runs as a persistent daemon.

## 1. Commands

Execute from the workspace root (see root `AGENTS.md` for lint, format, and test commands):

| Task               | Command                                     | Description                                                                     |
| :----------------- | :------------------------------------------ | :------------------------------------------------------------------------------ |
| **Ingest Articles**| `npx nx run hermes-worker:ingest-articles`  | Sync sources, fetch due feeds, write the ledger, then label, embed, and assign syndication families |
| **Build Events**   | `npx nx run hermes-worker:build-events`     | Cluster articles into events, synthesize descriptions, score, assign threads, and reconcile/merge duplicate events |
| **Audit Sources**  | `npx nx run hermes-worker:audit-sources`    | Probe configured feeds and sample articles read-only                            |
| **Maintain Events**| `npx nx run hermes-worker:maintain-events`  | Requeue stale claims, apply event and thread lifecycle transitions, reconcile aggregate counts, and apply retention |
| **Healthcheck**    | `npx nx run hermes-worker:healthcheck`      | Check database connectivity, schema, queue depth, and stale claims               |
| **Reset DB**       | `npx nx run hermes-worker:reset-db`         | Drop local database objects only; guarded by `--yes` and a local-target check    |

Do not reintroduce a `pipeline-*` command or a feature flag that shadows a real command.

## 2. Boundaries

- **Execution Approval**: `ingest-articles`, `build-events`, and `maintain-events` mutate the database. Never execute them without explicit user approval (and verify `DB_HOST` in `.env` first per root `AGENTS.md`).
- **Read-Only Probe**: `healthcheck` and `audit-sources` must not write rows. `healthcheck` may be run during an incident without approval; `audit-sources` performs outbound network probes but never writes the database or the source config.
- **Network Isolation in Tests**: All tests in `tests/` are mocked. Never write tests that hit the network, call external APIs, or query a live database. Database tests use the `integration` marker and skip without `TEST_DATABASE_URL`.

## 3. Invariants

- **Connection Lifespan**: Every database-backed CLI handler must execute inside `db_lifespan()` (`core/lifespan.py`) to guarantee connection disposal on exit. `audit-sources` is network-only and intentionally runs without a database session.
- **One Command, One Job**: Commands live in `jobs/commands.py`; stage order and locking live there, not in handlers. Handlers only translate CLI arguments.
- **Stage Contract**: Every stage implements `jobs.context.Stage`, receives a `JobContext`, returns `StageStats`, and owns its transaction boundary. Domain services never commit.
- **Claim-Based Work**: Stages claim articles via `ArticleQueue` (`FOR UPDATE SKIP LOCKED`) rather than scanning and mutating rows in place. The queue never commits.
- **Ledger Identity**: Every ingested row stores `canonical_url` and `canonical_url_hash`. Ingest inserts with `ON CONFLICT DO NOTHING`; it never updates or revives an existing article row. `duplicate_of_id` is set only by explicit reconciliation.
- **Source Config Ownership**: `sources.json` owns feed URLs, provider, fallback, paywall, and fetch policy. The ingest stage syncs and commits those fields; other commands never sync sources.
- **Transient Bodies**: Never persist fetched article bodies. `BodyFetcher` validates every redirect hop (SSRF), obeys robots.txt, caps response size, and returns text only for successful fetches. Paywalled and `SUMMARY_ONLY` sources label from `feed_summary`.
- **Label Gate**: Persist every label, including rejected ones, with `reject_stage` and a bounded reason. Never embed a rejected label or create a family for it. Evidence quotes must be validated against supplied text; the LLM never supplies coordinates.
- **Bounded LLM Spend**: Reserve calls through `JobContext.budget` before invoking `complete_json` or embedding. When the budget is exhausted, `ANALYZE` stops before the next group, releases the in-flight claims, and returns; never run unbounded.
- **No Run Telemetry Table**: The process exit code and structured logs are the execution record. Article claim fields (`claimed_at`, `claimed_by`, `attempt_count`, `last_error`) are the durable work state. Do not add a run-telemetry table without a concrete query that cannot be served by logs or domain rows.
- **Telemetry Flush on Exit**: Ensure `LlmService.aclose()` -> `get_client().flush()` executes on process exit so buffered Langfuse telemetry flushes before ephemeral Fargate container teardown.
- **Failure Exit**: Exit with a non-zero status code (`sys.exit(1)`) on unhandled exceptions or execution failures.

## 4. Runtime & Memory

The worker runs in production as a scheduled AWS Fargate task (0.25 vCPU, 512 MB RAM, ephemeral one-shot container) with no state between invocations. Process feeds in bounded batches using the concurrency semaphore and the `ARTICLE_*` limits; never accumulate all feeds or articles in memory. For container entrypoints and deployment configuration, inspect `apps/hermes-worker/Dockerfile` and `.github/workflows/cd-worker.yml`.

## 5. Tunables

Changing any of these requires explaining the expected effect and obtaining approval:

- Claim queue: `ARTICLE_CLAIM_BATCH_SIZE`, `ARTICLE_CLAIM_STALE_MINUTES`, `ARTICLE_MAX_ATTEMPTS` in `apps/hermes-worker/src/hermes_worker/core/config.py`
- Ingest window: `ARTICLE_MAX_AGE_HOURS`, `ARTICLE_FUTURE_SKEW_HOURS`, `SOURCE_FETCH_CONCURRENCY` in `apps/hermes-worker/src/hermes_worker/core/config.py`
- Analysis batches: `ARTICLE_ANALYZE_BATCH_SIZE`, `ARTICLE_LABEL_BATCH_SIZE` in `apps/hermes-worker/src/hermes_worker/core/config.py`
- Transient fetch: `ARTICLE_FETCH_CONNECT_TIMEOUT_SECONDS`, `ARTICLE_FETCH_READ_TIMEOUT_SECONDS`, `ARTICLE_BODY_MIN_CHARS`, `ARTICLE_FETCH_MAX_BYTES`, `ARTICLE_FETCH_MAX_REDIRECTS`, `ARTICLE_FETCH_PER_HOST_CONCURRENCY` in `apps/hermes-worker/src/hermes_worker/core/config.py`
- Syndication families: `ARTICLE_FAMILY_WINDOW_DAYS`, `ARTICLE_FAMILY_MAX_CANDIDATES` in `apps/hermes-worker/src/hermes_worker/core/config.py`; match thresholds in `apps/hermes-worker/src/hermes_worker/jobs/families.py`
- Event clustering: `EVENT_CLUSTER_BATCH_SIZE`, `EVENT_CLUSTER_WAVE_SIZE`, `EVENT_CLUSTER_WINDOW_DAYS`, `EVENT_CLUSTER_ANN_LIMIT`, `EVENT_CLUSTER_COUNTRY_LIMIT`, `EVENT_CLUSTER_CANDIDATE_CAP`, `EVENT_CLUSTER_ADJUDICATION_BATCH_SIZE`, `EVENT_CLUSTER_LLM_PAIRS_PER_RUN` in `apps/hermes-worker/src/hermes_worker/core/config.py`; pairwise thresholds (`AUTO_ATTACH_THRESHOLD = 0.80`, `LLM_BAND_THRESHOLD = 0.60`) in `apps/hermes-worker/src/hermes_worker/jobs/pair_score.py`
- Event description: `EVENT_DESCRIBE_BATCH_SIZE`, `EVENT_DESCRIBE_MAX_FAMILIES` in `apps/hermes-worker/src/hermes_worker/core/config.py`
- Event scoring: `EVENT_SCORE_PAGE_SIZE` in `apps/hermes-worker/src/hermes_worker/core/config.py`; scoring weights and thresholds in `libs/shared/hermes-db/src/hermes_db/services/event_scoring.py`
- Story threads: `THREAD_EVENT_LIMIT`, `THREAD_CANDIDATE_LIMIT`, `THREAD_ADJUDICATION_BATCH_SIZE`, `THREAD_LLM_PAIRS_PER_RUN`, `THREAD_MIN_GROUP` in `apps/hermes-worker/src/hermes_worker/core/config.py`; `THREAD_DORMANT_DAYS = 7`, `THREAD_ENDED_DAYS = 30`, `THREAD_IMPORTANCE_HALF_LIFE_HOURS = 168.0` in `libs/shared/hermes-db/src/hermes_db/services/thread.py`
- Event merge & reconciliation: `EVENT_RECONCILE_WINDOW_HOURS`, `EVENT_RECONCILE_LIMIT`, `EVENT_MERGE_LLM_PAIRS_PER_RUN` in `apps/hermes-worker/src/hermes_worker/core/config.py`; pair thresholds (`MERGE_AUTO_THRESHOLD = 0.92`, `MERGE_GRAY_THRESHOLD = 0.85`) in `apps/hermes-worker/src/hermes_worker/jobs/pair_score.py`
- Lifecycle cutoffs: `DEFAULT_STALE_HOURS` and `DEFAULT_ARCHIVE_HOURS` in `libs/shared/hermes-db/src/hermes_db/services/event_lifecycle.py`; `EVENT_STALE_HOURS` and `EVENT_ARCHIVE_HOURS` in `apps/hermes-worker/src/hermes_worker/core/config.py`
- Data retention: `cluster_decisions` (90d), removed `event_members` (180d), archived embeddings (30d) in `libs/shared/hermes-db/src/hermes_db/services/maintenance.py`
- Per-run LLM budget: `MAX_LLM_CALLS_PER_RUN` in `apps/hermes-worker/src/hermes_worker/core/config.py`

## 6. Triggers (Code Modifications Only)

- **When modifying stage order, claim semantics, thresholds, decay, or scheduling**: Read `apps/hermes-worker/docs/architecture.md`.
- **When modifying clustering thresholds or pair-scoring weights**: Read `apps/hermes-worker/src/hermes_worker/jobs/pair_score.py` and `apps/hermes-worker/src/hermes_worker/jobs/cluster.py`.
- **When modifying scoring formula, tiers, or lifecycle cutoffs**: Read `libs/shared/hermes-db/src/hermes_db/services/event_scoring.py` and `libs/shared/hermes-db/src/hermes_db/services/event_lifecycle.py`.
- **When modifying thread assignment or lifecycle**: Read `libs/shared/hermes-db/src/hermes_db/services/thread.py` and `apps/hermes-worker/src/hermes_worker/jobs/thread_assignment.py`.
- **When modifying merge policy or reconciliation**: Read `libs/shared/hermes-db/src/hermes_db/services/event_merge.py` and `apps/hermes-worker/src/hermes_worker/jobs/reconcile.py`.
- **When modifying geocoding logic, rate limits, or caches**: Read `libs/shared/hermes-ai/AGENTS.md`.
