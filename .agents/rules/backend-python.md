---
trigger: always_on
description: Strict rules for Python, FastAPI, and Database operations.
---

# Backend & Python Standards

- **Strict Dependency Injection**: NEVER instantiate database sessions or heavy services inside a FastAPI route. ALWAYS use FastAPI's `Depends()` injection system.
- **Strict Type Hinting**: ALWAYS add explicit Python type hints for EVERY function argument and return type. Untyped functions are strictly forbidden. Use `snake_case` for Python variables and functions.
- **SQLAlchemy 2.0 Async**: Strictly write queries using the modern SQLAlchemy 2.0 Async style (e.g., `select()`, `await session.execute()`). The legacy 1.x `session.query()` approach is forbidden.
- **Strict Pydantic v2**: All API payloads, GenAI schemas, and internal data transfers MUST be typed as Pydantic v2 `BaseModel`s. Raw dictionaries are forbidden for structured data.
- **Ruff Exclusivity**: Strictly adhere to the `ruff` configuration in `pyproject.toml`. Do not introduce `black`, `flake8`, or `isort`.
- **Strict Async/Await**: NEVER write blocking, synchronous I/O code (like `requests.get` or `time.sleep`) inside FastAPI endpoints. Strictly use `httpx.AsyncClient` and `asyncio.sleep()`.
- **Exception Handling**: NEVER return raw dictionaries for errors. Strictly `raise HTTPException(status_code=...)` so middleware handles them uniformly. Log unexpected exceptions (500s) using `logging.exception("...")` to capture tracebacks.
- **Database Migrations**: NEVER modify database tables via raw SQL scripts or `create_all()`. Every schema change MUST be accompanied by an Alembic migration script.
- **GeoAlchemy Native**: Strictly use `geoalchemy2.functions` (e.g., `func.ST_Intersects()`) instead of injecting raw SQL strings for PostGIS operations.
- **Documentation**: Write Google-style docstrings for all Python service functions and complex endpoints.
- **Modular Routers**: Strictly use `APIRouter` to split endpoints into domain-specific modules. Defining all routes in a monolithic `main.py` is forbidden.
- **Python Imports**: Strictly use absolute imports in Python (e.g., `from src.services.db import get_db`) and avoid relative dot imports.
