# Hermes DB (`libs/shared/hermes-db`)

Foundational asynchronous persistence library providing SQLAlchemy 2.0 models, PostGIS spatial queries, and pgvector HNSW indexing.

## 1. Commands

Run commands from the workspace root using project `hermes-db`. See root `AGENTS.md` Commands table for migration, lint, and test commands.

| Task     | Command                 |
| :------- | :---------------------- |
| **Lint** | `npx nx lint hermes-db` |
| **Test** | `npx nx test hermes-db` |

## 2. Invariants

- **Unidirectional Dependency**: Never import anything from consumer applications (`apps/hermes-api`, `apps/hermes-worker`, `apps/hermes`).
- **Engine Lifecycle IoC**: Consumer applications validate their environment and pass connection URLs to `init_db(db_url)`. Standalone tooling (Alembic CLI) reads configuration directly via internal `Settings`.
- **Domain Logic Boundary**: Do not introduce business workflows, LLM prompting, or ingestion pipelines here.
- **Statement Caching**: Always pass `connect_args={"statement_cache_size": 0}` to `create_async_engine` to maintain compatibility with PgBouncer transaction pooling in Neon Serverless.
- **Direct Coordinate Projection**: Project coordinates via `ST_X` and `ST_Y` directly inside SQL queries rather than deserializing WKB geometry objects on the client.
- **Code Conventions**: Follow `.agents/rules/python-standards.md` for all Python coding standards (typing, absolute imports, enum usage, parameterized logging).

## 3. Tunables

- Similarity threshold: Cosine distance literal in `libs/shared/hermes-db/src/hermes_db/services/event.py`
- Credibility & decay: `CREDIBILITY_WEIGHTS` and `HOURLY_DECAY_FACTOR` in `libs/shared/hermes-db/src/hermes_db/services/ranking.py`
- Lifecycle cutoffs: `EVENT_STALE_HRS` and `EVENT_ARCHIVE_HRS` in `libs/shared/hermes-db/src/hermes_db/core/config.py`
- Vector index parameters: `M` and `ef_construction` in `libs/shared/hermes-db/src/hermes_db/models/event.py`

## 4. Domain Triggers

- **When modifying schemas, connection pooling, spatial queries, or vector indexes**: Read `libs/shared/hermes-db/docs/architecture.md`.
