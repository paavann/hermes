---
trigger: always_on
---

# Database Standards

## Database & ORM
- **SQLAlchemy 2.0 Async**: Strictly write queries using the modern SQLAlchemy 2.0 Async style (e.g., `select()`, `await session.execute()`). The legacy 1.x `session.query()` approach is forbidden.
- **MissingGreenlet Prevention**: In async SQLAlchemy, lazy loading triggers `MissingGreenlet`. Every relationship must specify explicit eager loading (e.g., `options(selectinload(...))`).
- **Transaction Discipline**: Read queries should never call `commit()`. Service mutation methods must clearly define whether they call `flush()` or `commit()`. Use `except BaseException:` for rollback cleanup to handle async cancellations properly.

## Schema Migrations (Alembic)
- **No Raw Modifications**: NEVER modify database tables via raw SQL scripts or `create_all()`. Every schema change MUST be accompanied by an Alembic migration script.
- **Append-Only History**: Never edit, rewrite, or squash historical migration scripts in `migrations/versions/`.
- **Explicit Type Verification**: Alembic autogenerate misinterprets spatial/vector types. You MUST manually verify that generated scripts explicitly declare `srid=4326`, `HALFVEC(2048)`, and specify `postgresql_using="gist"` or `"hnsw"`.

## Spatial & PostGIS
- **GeoAlchemy Native**: Strictly use `geoalchemy2.functions` (e.g., `func.ST_Intersects()`, `func.ST_X()`) instead of injecting raw SQL strings for PostGIS operations.
- **Coordinates**: Strictly WGS 84 (SRID 4326). Ordered `(longitude, latitude)`.

## Testing
- **100% Mocked Isolation**: Unit tests in this library must NEVER connect to a running database instance. Use the mock factory helpers in `tests/conftest.py` (`make_async_session`, etc.) and verify queries via side-effect tracking.
