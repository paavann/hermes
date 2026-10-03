---
trigger: always_on
---

# Database Standards

## Database

- **SQLAlchemy 2.0 Async**: Strictly write queries using the modern SQLAlchemy 2.0 Async style (e.g., `select()`, `await session.execute()`). The legacy 1.x `session.query()` approach is forbidden.
- **Database Migrations**: NEVER modify database tables via raw SQL scripts or `create_all()`. Every schema change MUST be accompanied by an Alembic migration script.
- **GeoAlchemy Native**: Strictly use `geoalchemy2.functions` (e.g., `func.ST_Intersects()`) instead of injecting raw SQL strings for PostGIS operations.
