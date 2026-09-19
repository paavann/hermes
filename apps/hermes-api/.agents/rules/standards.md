---
trigger: always_on
---

# Backend & Python Standards

- **Strict Dependency Injection**: NEVER instantiate database sessions or heavy services inside a FastAPI route. ALWAYS use FastAPI's `Depends()` injection system.
- **Strict Type Hinting**: ALWAYS add explicit Python type hints for EVERY function argument and return type. Untyped functions are strictly forbidden. Use `snake_case` for Python variables and functions.
- **SQLAlchemy 2.0 Async**: Strictly write queries using the modern SQLAlchemy 2.0 Async style (e.g., `select()`, `await session.execute()`). The legacy 1.x `session.query()` approach is forbidden.
- **Strict Pydantic v2**: All API payloads, GenAI schemas, and internal data transfers MUST be typed as Pydantic v2 `BaseModel`s. Raw dictionaries are forbidden for structured data.
- **Strict Enum Usage**: ALWAYS use Python `enum.Enum` (specifically `(str, enum.Enum)`) wherever appropriate when handling a fixed set of status, scope, type, category, or tier values. Hardcoding raw string literals across services, models, schemas, or status updates is strictly forbidden.
- **Ruff Exclusivity**: Strictly adhere to the `ruff` configuration in `pyproject.toml`. Do not introduce `black`, `flake8`, or `isort`.
- **Strict Async/Await**: NEVER write blocking, synchronous I/O code (like `requests.get` or `time.sleep`) inside FastAPI endpoints. Strictly use `httpx.AsyncClient` and `asyncio.sleep()`.
- **Custom Exception Handling**: ALWAYS use custom application exceptions (derived from `AppException`) rather than generic exceptions or raw error dicts. Exception handling must strictly be managed through FastAPI custom exception handlers registered at the application level.
- **Parameterized Logging**: ALWAYS use parameterized string formatting (e.g., `logger.info("Message %s", var)` or `logger.exception("Failed %s", var)`) across all logger levels (`debug`, `info`, `warning`, `error`, `exception`). Using f-strings or `.format()` inside logger calls is strictly forbidden to preserve deferred evaluation, performance short-circuiting, and structured log aggregation.
- **Developer Log Formatting**: All internal developer log messages (which are for internal observability and never sent to API clients) MUST start with a lowercase letter (never capitalized) and MUST always end with a period (`.`). If a log message consists of multiple sentences, periods must be included in-between sentences as well (e.g., `logger.info("fetching event %s. timeline generation starting.", event_id)`).
- **Database Migrations**: NEVER modify database tables via raw SQL scripts or `create_all()`. Every schema change MUST be accompanied by an Alembic migration script.
- **GeoAlchemy Native**: Strictly use `geoalchemy2.functions` (e.g., `func.ST_Intersects()`) instead of injecting raw SQL strings for PostGIS operations.
- **Documentation**: Write Google-style docstrings for all Python service functions and complex endpoints.
- **Modular Routers**: Strictly use `APIRouter` to split endpoints into domain-specific modules. Defining all routes in a monolithic `main.py` is forbidden.
- **Python Imports**: Strictly use absolute imports in Python (e.g., `from src.services.db import get_db`) and avoid relative dot imports.
