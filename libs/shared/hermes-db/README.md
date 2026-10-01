# Hermes Database

Shared PostGIS and pgvector data access layer, declarative ORM models, Alembic migrations, and database transaction services for Project Hermes.

---

## 1. Architectural Role & Inversion of Control

`hermes-db` is an independent, pure Python library designed to be consumed by application runtime shells (such as `hermes-api`) and background worker jobs.

### Host-Injected Connection Configuration

To prevent configuration drift across monorepo packages, `hermes-db` relies on **Inversion of Control (IoC)**:

- The host application (e.g. `hermes-api`) loads and validates runtime environment credentials (via `.env`, `.env.development`, or container secrets).
- During startup lifespan, the host passes its validated database URL directly to `init_db`:

  ```python
  from hermes_db import init_db, close_db

  # In application startup lifespan:
  await init_db(db_url=settings.db_url)
  ```

- `init_db(db_url)` rebinds the active async engine and updates `AsyncSessionLocal` in-place, ensuring all importing services seamlessly use the injected connection pool.
- On shutdown, `await close_db()` safely disposes of the connection pool.

---

## 2. Models & Schema

The library defines declarative SQLAlchemy 2.0 models with spatial and vector extensions:

- **`Event`**: Core news event entity with PostGIS `Geometry(POINT, 4326)` for coordinates, pgvector `halfvec(2048)` for semantic embeddings with HNSW indexing, trending scores, and lifecycle statuses (`ACTIVE`, `STALE`, `ARCHIVED`).
- **`Article`**: Individual news stories associated with events, tracking source provenance, titles, URLs, and publication timestamps.
- **`Source`**: Curated RSS publishers and news feeds with credibility tier assignments (`TIER_1` through `TIER_4`).
- **`GeocodeCache`**: Persistent geocoding cache mapping normalized place names to latitude/longitude coordinates to shield external geocoding providers.
- **`EventTl`**: Historical causality timeline graphs stored as JSONB nodes and causal edges.

---

## 3. Services

The library provides dedicated async services operating over `AsyncSession`:

- **`EventService`**: Querying events by bounding box (`ST_Within`), trending score, and vector similarity; creating events; and executing hourly lifecycle score decay.
- **`ArticleService`**: Article persistence and URL deduplication.
- **`GeocodeCacheService`**: Spatial cache lookup and storage.
- **`EventTlService`**: Timeline graph retrieval, generation lifecycle tracking, and node/edge persistence.
- **`sync_sources_from_config`**: Synchronizes publisher definitions from `sources.json` into the database.

---

## 4. Migrations & CLI Usage

Alembic migrations reside inside this library (`migrations/`).

To run migrations:

```bash
# From workspace root
npx nx migrate hermes-db

# Or directly via uv inside the library
uv run alembic upgrade head
```

During standalone CLI executions, Alembic falls back to reading the root `.env.development` (or `.env.production` when `ENV=production` is set).
