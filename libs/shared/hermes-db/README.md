# `hermes-db`

Shared asynchronous persistence library for Hermes. It defines the SQLAlchemy 2.0 models, PostGIS geometry, pgvector HNSW indexes, domain services, and Alembic migrations used by both `hermes-api` and `hermes-worker`.

## Responsibilities

- Own the database schema as the single source of truth: `Source`, `Article`, `Event`, `EventTl`, and `GeocodeCache`.
- Provide async services for ingestion, event lifecycle, ranking, hybrid search, timelines, and geocode caching.
- Initialize the engine and session factory from a URL supplied by the consumer.
- Apply every schema change through Alembic.

The library never reads `.env` files or `os.environ`. Consumers validate configuration and call `init_db()` at startup. Alembic's `migrations/env.py` is the only standalone resolver.

## Models

| Model | Table | Notes |
| :--- | :--- | :--- |
| `Source` | `sources` | Publisher/feed configuration, soft-disabled via `is_active`. |
| `Article` | `articles` | Globally unique URL, cascading event/source FKs, `source` relationship eager-loaded with `selectin`. |
| `Event` | `events` | Denormalized map/feed aggregate with `geometry(POINT, 4326)`, `halfvec(2048)` embedding, score, velocity, and lifecycle timestamps. |
| `EventTl` | `event_timelines` | One-to-one timeline graph stored as JSONB `nodes`/`edges`. |
| `GeocodeCache` | `geocode_cache` | Normalized location-name cache; `NULL` coordinates act as a negative cache. |

All `datetime` columns map to `TIMESTAMPTZ`, and application code writes aware UTC. `Event.articles` uses `lazy="raise"`; read paths must eager-load it explicitly.

## Services

| Service | Focus |
| :--- | :--- |
| `ArticleService` | URL existence checks and idempotent article creation. |
| `EventService` | Event creation, corroboration, bbox queries, active-context queries, and lifecycle transitions. |
| `SearchService` | Hybrid lexical + semantic retrieval with RRF, scope filters, coverage classification, and context hydration. |
| `SourceService` | Due-source selection, fetch cursors, and source-catalog sync. |
| `EventTlService` | Timeline creation, status transitions, generated-graph persistence, and deletion. |
| `GeocodeCacheService` | First-write-wins geocode cache with negative-cache semantics. |
| `ranking` | Credibility weights, diversity, velocity, and time-decay scoring helpers. |

## Session Lifecycle

```python
from hermes_db import close_db, get_db, init_db

await init_db("postgresql+asyncpg://user:pass@host/hermes")
# FastAPI: session = Depends(get_db)
await close_db()
```

`init_db()` creates an `AsyncEngine` with `pool_pre_ping=True` and `statement_cache_size=0` (required for PgBouncer transaction pooling), probes connectivity, and syncs the source catalog. `get_db()` yields an `AsyncSession` and rolls back on exceptions.

## Migrations

The chain is linear: 16 revisions from root `2ec3541646e8` to head `9e1bb45d1cba`. Revision 16 hardened timestamps to `TIMESTAMPTZ` and added the missing `articles.updated_at` and `geocode_cache.updated_at` columns.

```bash
npx nx run hermes-db:makemigrations -- -m "<message>"
npx nx run hermes-db:migrate
```

Never edit an applied revision or use `Base.metadata.create_all()`.

## Commands

```bash
npx nx lint hermes-db
npx nx test hermes-db
npx nx run hermes-db:format
```

## Related Docs

- [`AGENTS.md`](AGENTS.md) — invariants and tunables.
- [`docs/architecture.md`](docs/architecture.md) — schema, query design, migration chain, and ADRs.
