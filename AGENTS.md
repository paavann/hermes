# Hermes Workspace

Workspace instructions for AI agents. All commands run from the monorepo root (`.`). Never `cd` into child directories. List projects via `npx nx show projects`; each application and library maintains its own nested `AGENTS.md` for domain-specific details.

## 1. Commands

All commands run from the workspace root:

| Task                      | Command                                                                             |
| :------------------------ | :---------------------------------------------------------------------------------- |
| **Install**               | `npm ci && uv sync`                                                                 |
| **Dev (UI)**              | `npx nx dev hermes`                                                                 |
| **Dev (API)**             | `npx nx serve hermes-api`                                                           |
| **Dev (DB)**              | `docker compose up -d hermes-db`                                                    |
| **Create Migration**      | `npx nx run hermes-db:makemigrations -- -m "<msg>"`                                |
| **Apply Migration**       | `npx nx run hermes-db:migrate`                                                      |
| **Lint**                  | `npx nx lint <project>`                                                             |
| **Typecheck**             | `npx nx typecheck <project>`                                                        |
| **Test (Suite)**          | `npx nx test <project>`                                                             |
| **Test (Single TS File)** | `npx nx test <project> -- path/to/file.spec.ts`                                     |
| **Test (Single TS Case)** | `npx nx test <project> -- -t "<test_name>"`                                         |
| **Test (Single Py File)** | `npx nx test <project> -- tests/path/to/test_file.py`                                |
| **Test (Single Py Case)** | `npx nx test <project> -- -k <test_name>`                                           |
| **Format (TS)**           | `npx nx format:write --projects=<project>`                                          |
| **Format (Python)**       | `npx nx run <project>:format`                                                       |
| **Affected Check**        | `npx nx affected -t lint typecheck test --base=master`                              |

## 2. Invariants

- **Coordinates**: Derive coordinates exclusively via the geocoding pipeline in `libs/shared/hermes-ai` (cached, token-bucket rate-limited Nominatim client). Never accept LLM-generated coordinates; never call Nominatim directly (1 req/s policy).
- **Database Schemas**: Apply all schema alterations through Alembic migrations only. Raw SQL DDL and `create_all()` are strictly prohibited.
- **Contract Synchronization**: TypeScript response models in `libs/shared/util-types/src/lib/api-types.ts` are hand-mirrored from Pydantic schemas in `apps/hermes-api/src/hermes_api/schemas/events.py`. Update both together in the same task whenever contracts change.

## 3. Conventions

- **Thin Shells (`apps/` vs `libs/`)**: Applications in `apps/` contain routing, document shells, and top-level provider wiring only. All business logic, state stores, spatial math, and UI widgets reside in `libs/`.
- **Modular Feature Structure**: Decompose features into dedicated directories containing `index.ts` (public export), `types.ts` (contracts), `use-[feature].ts` (logic/state hook), and isolated subcomponent files. Avoid monolithic single-file implementations.
- **UI Primitives**: Install shadcn primitives via `npx shadcn@latest add <component> --cwd libs/shared/ui-components`. Place shared UI elements in `libs/shared/ui-components`, never inside `apps/hermes`.
- **Generators vs Manual Files**: Use Nx generators (`npx nx g ...`) exclusively when creating new monorepo libraries or applications. Internal feature files (`types.ts`, hooks, components) are created directly by hand.
- **Dependencies**: Adding, updating, or removing any dependency requires explicit user approval. Once approved, prefer the Nx target (e.g. `npx nx run <project>:add --name=<pkg>`), falling back to `npm install` (Node) or `uv add` (Python).

## 4. Gotchas & Landmines

- **SSR WebGL Isolation**: `apps/hermes` runs in SSR mode (`ssr: true`), but Mapbox GL requires browser globals (`window`, WebGL context). Never render Mapbox canvas directly during SSR; isolate it behind dynamic `React.lazy` boundaries with a fallback skeleton.
- **Database Availability**: The PostGIS container must be running (`docker compose up -d hermes-db`) before starting the API or applying migrations to prevent connection refused errors.
- **`nx affected` Base Branch**: Nx defaults to `--base=main`, which fails because this repo uses `master`. Always pass `--base=master`.

## 5. Boundaries & Environment

- **Production Protection**: Never run migrations, the worker, or any script against a production database or with production API keys. Use `.env.example` to learn variable names; never read `.env` for values beyond the `DB_HOST` check above. Never place secret values in code or commits.
- **Migration History**: Never edit existing migration files in `libs/shared/hermes-db/migrations/versions/`; always create a new migration via the Alembic revision command.
- **Mandatory Approvals**: Agents must obtain explicit user approval before:
  1. Adding, updating, or removing dependencies in `package.json` or `pyproject.toml`.
  2. Executing database migrations (`npx nx run hermes-db:migrate`).
  3. Running `git commit` or `git push` (leave version control execution to the user).
  4. Modifying `.env` files or security credentials.
- **Protected Files**: Never manually edit lockfiles (`package-lock.json`, `uv.lock`).
- **Verification**: After completing a code task, run the Affected Check command from the Commands table. Skip it for conversational questions and intermediate edits; a targeted single check to debug a failure is fine.
- **Environment Reference**: Consult `.env.example` for required workspace variables (`ENV`, `API_PORT`, `FRONTEND_PORT`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `VITE_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`) and `apps/hermes-api/.env.example` for AI keys (`LLM_API`, `LLM_MODEL`, `EMBED_API`, `EMBED_MODEL`). Never place secret values in code or commits.

## 6. Domain Triggers

- **When editing React UI or routes (`apps/hermes/`)**: Read `apps/hermes/AGENTS.md` and `.agents/rules/react-standards.md`.
- **When editing Mapbox GL layers, telemetry, or clustering (`libs/map/`)**: Read `libs/map/AGENTS.md`.
- **When editing REST endpoints or causality timelines (`apps/hermes-api/`)**: Read `apps/hermes-api/AGENTS.md`.
- **When editing RSS ingestion, Fargate worker, or geocoding (`apps/hermes-worker/` or `libs/shared/hermes-ai/`)**: Read `apps/hermes-worker/AGENTS.md` and `libs/shared/hermes-ai/AGENTS.md`.
- **When editing database schemas, models, or migrations (`libs/shared/hermes-db/`)**: Read `libs/shared/hermes-db/AGENTS.md`.
- **When writing Python code (`**/\*.py`)**: Read `.agents/rules/python-standards.md`.
- **When writing TypeScript code (`**/_.ts`, `\*\*/_.tsx`)**: Read `.agents/rules/ts-standards.md`.
