# Hermes DB (`libs/shared/hermes-db`)

Foundational asynchronous persistence library providing SQLAlchemy 2.0 models, PostGIS spatial queries, and pgvector HNSW indexing. Run all Nx commands from the workspace root using project `hermes-db`.

## 1. Invariants

- **Unidirectional Dependency**: Never import anything from consumer applications (`apps/hermes-api`, `apps/hermes-worker`, `apps/hermes`).
- **Engine & Config IoC**: Never read `.env` or `os.environ` inside `src/hermes_db/`. Consumer applications validate environment variables and pass connection URLs into `init_db(db_url)` (Alembic's `migrations/env.py` is the only allowed standalone resolver).
- **Domain Logic Boundary**: Do not introduce business workflows, LLM prompting, or ingestion pipelines here.
- **Statement Caching**: Always pass `connect_args={"statement_cache_size": 0}` to `create_async_engine` to maintain compatibility with PgBouncer transaction pooling in Neon Serverless.
- **Direct Coordinate Projection**: Project coordinates via `ST_X` and `ST_Y` directly inside SQL queries rather than deserializing WKB geometry objects on the client.
- **Migrations Only**: Every schema change goes through Alembic. Never use raw DDL or `Base.metadata.create_all()`; never edit an already-applied revision.

## 2. Tunables

- Verification derivation: `compute_verification` and `_origin_key` in `libs/shared/hermes-db/src/hermes_db/services/verification.py`
- Similarity & read queries: `cosine_distance` thresholds in `libs/shared/hermes-db/src/hermes_db/services/event_assignment.py` and `libs/shared/hermes-db/src/hermes_db/services/event_relationship.py`
- Event scoring: `SCORING_CREDIBILITY`, `IMPACT_VALUE`, `VERIFY_VALUE`, half-lives, and tier cutoffs in `libs/shared/hermes-db/src/hermes_db/services/event_scoring.py`
- Event lifecycle: `DEFAULT_STALE_HOURS` and `DEFAULT_ARCHIVE_HOURS` in `libs/shared/hermes-db/src/hermes_db/services/event_lifecycle.py`
- Thread lifecycle: `THREAD_DORMANT_DAYS`, `THREAD_ENDED_DAYS`, and `THREAD_IMPORTANCE_HALF_LIFE_HOURS` in `libs/shared/hermes-db/src/hermes_db/services/thread.py`
- Merge policy: `EventMergeService` survivor rules in `libs/shared/hermes-db/src/hermes_db/services/event_merge.py`; pair thresholds live in `apps/hermes-worker/src/hermes_worker/jobs/pair_score.py`
- Vector index parameters: `M` and `ef_construction` in `libs/shared/hermes-db/src/hermes_db/models/event.py`

## 3. Domain Triggers (Code Modifications Only)

- **When modifying schemas, connection pooling, spatial queries, or vector indexes**: Inspect `src/hermes_db/session.py`, `src/hermes_db/models/`, and `migrations/env.py`.
