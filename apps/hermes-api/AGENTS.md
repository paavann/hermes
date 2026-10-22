# Hermes API (`apps/hermes-api`)

Stateless FastAPI REST API and on-demand historical timeline synthesis engine.

## 1. Commands

Run all commands from the workspace root using project `hermes-api`. See root `AGENTS.md` Commands table for lint, typecheck, test, and format.

| Task    | Command                   |
| :------ | :------------------------ |
| **Dev** | `npx nx serve hermes-api` |

## 2. Invariants

- **Stateless Operation**: Never add cron runners, background workers, or ingestion loops. All harvesting and decay belong in `hermes-worker`.
- **Dependency Injection**: Route handlers in `api/v1/` must never instantiate database sessions or services directly; consume them via FastAPI `Depends()`.
- **CORS Exception Headers**: Handlers in `core/errors.py` bypass Starlette's `CORSMiddleware`. Every custom exception handler must explicitly include origin headers via `_cors_headers(request)`.
- **Lifespan Pool Management**: Initialize and dispose database connection pools inside `lifespan` in `main.py` via `init_db` and `close_db`. Never initialize connections at module import time.
- **Graceful Degradation**: When LLM credentials are missing, keep the server operational for spatial queries and return HTTP 503 from timeline synthesis endpoints instead of crashing.
- **No Local ORM Models**: All database models and migrations reside in `libs/shared/hermes-db`. Never define SQLAlchemy models in `hermes-api`.

## 3. Domain Triggers

- **When modifying endpoints, timeline synthesis pipeline, or error handling**: Read `apps/hermes-api/docs/architecture.md`.
