# Hermes DB — AI Agent Context & Brain

This document provides library-specific architectural context, technical standards, and non-negotiable conventions for the `hermes-db` shared library. It is scoped to `libs/shared/hermes-db/` and supplements the root `AGENTS.md`.

---

## 1. Library Role & Core Mandate

`hermes-db` is the **shared, low-level PostGIS and pgvector data access layer** for Project Hermes. It is a pure Python library managed with `uv` and built with **SQLAlchemy 2.0 (Async)**, **GeoAlchemy2**, **pgvector**, and **Alembic**.

### Strict Architectural Boundaries
- **Strict Low-Level Data Access**: This library is strictly responsible for declarative ORM models, database migrations, connection pooling, and low-level spatial/vector queries.
- **No Domain Business Logic**: Business workflows, AI extraction, and domain algorithms belong in the consumer applications (e.g. `hermes-api`). *Note: Existing domain logic in `hermes-db` (such as `CREDIBILITY_WEIGHTS` and `run_lifecycle_transitions`) is recognized technical debt slated for migration to application/domain services. Do NOT introduce new domain logic into this library.*
- **Unidirectional Monorepo Dependency**: `hermes-db` must NEVER import anything from consumer applications (`apps/hermes-api`, `apps/hermes`). All dependencies flow strictly inward: `apps -> libs`.

### Inversion of Control (Host-Injected Connections)
To prevent environment configuration drift and packaging issues in containerized deployments, `hermes-db` operates under **Inversion of Control (IoC)**:
- **Runtime Consumer Authority**: The consumer application (e.g. `hermes-api`) is the sole authority on runtime environment configuration. It loads `.env`, `.env.development`, or container secrets and passes its validated database URL to `init_db`:
  ```python
  from hermes_db import init_db, close_db

  # Called during application startup lifespan:
  await init_db(db_url=settings.db_url)
  ```
- **In-Place Reconfiguration**: `init_db(db_url)` rebinds the underlying engine and invokes `AsyncSessionLocal.configure(bind=engine)`. This guarantees reference identity across all services and route handlers that already imported `AsyncSessionLocal`.
- **Standalone CLI Fallback**: For standalone developer commands (`npx nx migrate hermes-db` or `uv run alembic upgrade head`), `hermes-db`'s internal `Settings` gracefully falls back to inspecting the root workspace `.env.{env}` files.

---

## 2. Spatial & Vector Database Architecture

The PostgreSQL database uses PostGIS 3.4+ and pgvector 0.7+ extensions. AI agents modifying schemas or writing queries must adhere to these specifications:

### Spatial Schema (PostGIS)
- **Coordinate System**: Strictly **WGS 84 (SRID 4326)**.
- **Geometry Type**: Point geometries (`Geometry(geometry_type="POINT", srid=4326)`). Coordinates are strictly ordered as `(longitude, latitude)` in WKT and GeoAlchemy2.
- **Indexing**: All spatial columns must be indexed with **GIST**:
  ```python
  Index("idx_events_location", "location", postgresql_using="gist")
  ```
- **Viewport Queries**: Viewport queries must use `ST_MakeEnvelope(west, south, east, north, 4326)` with `ST_Within(Event.location, bbox_poly)`. Longitude and latitude must be extracted via `ST_X` and `ST_Y`.

### Vector Schema (pgvector Half-Precision)
- **Vector Type**: Strictly **`HALFVEC(2048)`** (16-bit half-precision floating-point vectors matching `nemotron-3-embed-1b`). This halves memory usage compared to standard 32-bit floats with zero loss in search quality.
- **Indexing**: HNSW index using cosine distance operator:
  ```python
  Index(
      "idx_events_embedding",
      "embedding",
      postgresql_using="hnsw",
      postgresql_with={"M": "16", "ef_construction": "64"},
      postgresql_ops={"embedding": "halfvec_cosine_ops"},
  )
  ```
- **Semantic Distance Threshold**: Duplicate event detection evaluates cosine distance against active events:
  ```python
  Event.embedding.cosine_distance(embedding) < 0.25
  ```

---

## 3. SQLAlchemy 2.0 Async Coding Standards

All code in this library must follow modern SQLAlchemy 2.0 async conventions. Legacy 1.x patterns are strictly forbidden:

### Declarative 2.0 Mapping
- Use `Mapped[...]` and `mapped_column(...)` with explicit Python type annotations.
- Primary keys must use UUIDs via `UUIDPrimaryKeyMixin` (`uuid.uuid4`).
- Timestamps must inherit from `TimestampMixin` (`created_at`, `updated_at` with UTC timezone awareness).

### Relationship Loading & `MissingGreenlet` Prevention
- In async SQLAlchemy, lazy loading is impossible and triggers `sqlalchemy.exc.MissingGreenlet`.
- **Rule**: Every relationship must specify explicit eager loading when queried. Prefer `selectinload` for 1-to-many / many-to-many collections:
  ```python
  stmt = select(Event).options(selectinload(Event.articles)).where(Event.id == event_id)
  ```

### Session Lifecycle & Transaction Boundaries
- Always accept `AsyncSession` into service constructors:
  ```python
  class EventService:
      def __init__(self, session: AsyncSession) -> None:
          self._session = session
  ```
- **Transaction Discipline**: 
  - Read queries should never call `commit()`.
  - Service mutation methods must clearly define whether they call `flush()` (to acquire generated IDs within an ongoing transaction) or `commit()` (to complete the transaction boundary).
  - Never catch bare `except:`. Use `except BaseException:` when performing rollback cleanup in session generators to handle `asyncio.CancelledError` and `GeneratorExit` properly.

---

## 4. Migration & Schema Governance (Alembic)

Database schema migrations are append-only and strictly governed:

1. **Append-Only History**: Never edit, rewrite, or squash historical migration scripts in `migrations/versions/`. Every schema change requires a newly generated migration file.
2. **Generation Command**:
   ```bash
   # From workspace root
   npx nx migrate hermes-db
   ```
3. **Explicit Type Verification**: Alembic autogenerate often misinterprets PostGIS and pgvector types. Always manually inspect generated migration files to ensure:
   - Geometry columns explicitly declare `srid=4326`.
   - Vector columns explicitly use `pgvector.sqlalchemy.HALFVEC(2048)`.
   - Indexes include their `postgresql_using="gist"` or `postgresql_using="hnsw"` arguments.
4. **Reversible Migrations**: Every migration must implement a valid, tested `downgrade()` function that cleanly reverses all schema modifications.

---

## 5. Testing Philosophy: Pure Isolated Unit Tests

Testing in `hermes-db` follows a strict, non-negotiable philosophy:

- **100% Mocked Isolation (No Real Database)**:
  All unit tests in `libs/shared/hermes-db/tests/` are **pure unit tests**. They must never connect to or require a running PostgreSQL or PostGIS instance.
- **Mocking Harness (`conftest.py`)**:
  - Tests must utilize the shared mock factory helpers in `tests/conftest.py` (`make_async_session`, `make_event`, `make_article`, `make_source`).
  - SQLAlchemy `AsyncSession` methods (`execute`, `get`, `add`, `commit`, `rollback`) are mocked using `AsyncMock` and `MagicMock`.
  - Queries are verified by asserting that statement execution, parameters, and ORM side-effects match expectations.
- **Speed & Portability**: Tests must execute in milliseconds on any machine or CI pipeline without external Docker services. Integration tests that run against live PostGIS/pgvector instances belong strictly in higher-level end-to-end suites.

---

## 6. Project Structure

```text
libs/shared/hermes-db/
├── alembic.ini                   # Alembic configuration
├── pyproject.toml                # Library dependencies (uv, SQLAlchemy, PostGIS, pgvector)
├── project.json                  # Nx project targets (build, test, lint, migrate)
├── migrations/                   # Alembic migration environment
│   ├── env.py                    # Migration runner with PostGIS helpers and fallback config
│   └── versions/                 # Immutable append-only schema revision history
├── src/hermes_db/
│   ├── base.py                   # Declarative Base, UUIDPrimaryKeyMixin, TimestampMixin
│   ├── enums.py                  # Core domain enums (EventStatus, EventScope, CredibilityTier)
│   ├── session.py                # Async engine, AsyncSessionLocal, init_db(db_url), get_db()
│   ├── core/
│   │   └── config.py             # Minimal fallback Settings for standalone Alembic CLI
│   ├── data/
│   │   └── sources.json          # Curated RSS publisher seeds
│   ├── models/                   # Declarative SQLAlchemy 2.0 ORM models
│   │   ├── event.py              # Event model (PostGIS Point, pgvector halfvec(2048), indexes)
│   │   ├── article.py            # Article model (source URL, timestamps, foreign keys)
│   │   ├── source.py             # Source model (RSS publisher metadata and credibility tiers)
│   │   ├── geocode_cache.py      # GeocodeCache model (normalized location caching)
│   │   └── event_tl.py           # EventTl model (JSONB timeline nodes and causal edges)
│   └── services/                 # Pure database service classes
│       ├── event.py              # EventService (spatial queries, vector matching, event creation)
│       ├── article.py            # ArticleService (article creation, URL deduplication)
│       ├── geocode.py            # GeocodeCacheService (normalized place caching)
│       ├── source.py             # Source sync service (populates sources from sources.json)
│       └── tl.py                 # EventTlService (timeline graph storage and status tracking)
└── tests/                        # 100% Mocked Unit Test Suite
    ├── conftest.py               # Shared mock session and model factory fixtures
    ├── test_session.py           # Engine initialization, reconfiguration, and get_db tests
    ├── test_models.py            # ORM model property and relationship unit tests
    ├── test_event_service.py     # Spatial queries, vector similarity, and event service tests
    ├── test_article_service.py   # Article persistence and existence check tests
    ├── test_geocode_service.py   # Geocoding cache lookup and persistence tests
    └── test_source_service.py    # RSS source synchronization tests
```
