# Hermes DB (`libs/shared/hermes-db`)

Foundational asynchronous persistence library providing SQLAlchemy 2.0 models, PostGIS spatial queries, and pgvector HNSW indexing. Run all Nx commands from the workspace root using project `hermes-db`.

## 2. Invariants

- **Unidirectional Dependency**: Never import anything from consumer applications (`apps/hermes-api`, `apps/hermes-worker`, `apps/hermes`).
- **Engine & Config IoC**: Never read `.env` or `os.environ` inside `src/hermes_db/`. Consumer applications validate environment variables and pass connection URLs into `init_db(db_url)` (Alembic's `migrations/env.py` is the only allowed standalone resolver).
- **Domain Logic Boundary**: Do not introduce business workflows, LLM prompting, or ingestion pipelines here.
- **Statement Caching**: Always pass `connect_args={"statement_cache_size": 0}` to `create_async_engine` to maintain compatibility with PgBouncer transaction pooling in Neon Serverless.
- **Direct Coordinate Projection**: Project coordinates via `ST_X` and `ST_Y` directly inside SQL queries rather than deserializing WKB geometry objects on the client.

## 3. Tunables

- Similarity threshold: Cosine distance literal in `libs/shared/hermes-db/src/hermes_db/services/event.py`
- Credibility & decay: `CREDIBILITY_WEIGHTS` and `HOURLY_DECAY_FACTOR` in `libs/shared/hermes-db/src/hermes_db/services/ranking.py`
- Lifecycle cutoffs: `DEFAULT_EVENT_STALE_HRS` and `DEFAULT_EVENT_ARCHIVE_HRS` in `libs/shared/hermes-db/src/hermes_db/services/event.py`
- Vector index parameters: `M` and `ef_construction` in `libs/shared/hermes-db/src/hermes_db/models/event.py`

## 4. Domain Triggers (Code Modifications Only)

- **When modifying schemas, connection pooling, spatial queries, or vector indexes**: Inspect `src/hermes_db/session.py`, `src/hermes_db/models/`, and `migrations/env.py`.
