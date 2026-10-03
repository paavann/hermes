---
trigger: always_on
---

# Backend & FastAPI Standards

## Architecture & Framework (FastAPI)

- **Strict Dependency Injection**: NEVER instantiate database sessions or heavy services inside a FastAPI route. ALWAYS use FastAPI's `Depends()` injection system.
- **Strict Async/Await**: NEVER write blocking, synchronous I/O code (like `requests.get` or `time.sleep`) inside FastAPI endpoints. Strictly use `httpx.AsyncClient` and `asyncio.sleep()`.
- **Modular Routers**: Strictly use `APIRouter` to split endpoints into domain-specific modules. Defining all routes in a monolithic `main.py` is forbidden.
- **Custom Exception Handling**: ALWAYS use custom application exceptions (derived from `AppException`) rather than generic exceptions or raw error dicts. Exception handling must strictly be managed through FastAPI custom exception handlers registered at the application level.

## Models / Schemas

- **Strict Pydantic v2**: All API payloads, GenAI schemas, and internal data transfers MUST be typed as Pydantic v2 `BaseModel`s. Raw dictionaries are forbidden for structured data.
