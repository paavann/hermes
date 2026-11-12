# Hermes Workspace

Workspace instructions for AI agents. All commands run from the monorepo root (`.`). Never `cd` into child directories.

- **Apps**: `hermes` (React 19 SSR UI), `hermes-api` (FastAPI), `hermes-worker` (ingestion pipeline), `hermes-e2e` (Playwright)
- **Libs**: `chat`, `map`, `shared/hermes-ai`, `shared/hermes-db`, `shared/ui-components`, `shared/util-types`, `shared/utils/py`, `shared/utils/ts`
- **Tooling Scope**: Do NOT read, update, or generate files in `openspec/` or `graphify-out/` unless the user explicitly invokes an `/opsx-*` or `/graphify` workflow.

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
| **Affected Check**        | `CI=true npx nx affected -t lint typecheck test --base=master --open=false`          |

## 2. Invariants

- **Coordinates**: Derive coordinates exclusively via the geocoding pipeline in `libs/shared/hermes-ai` (cached, token-bucket rate-limited Nominatim client). Never accept LLM-generated coordinates; never call Nominatim directly (1 req/s policy).
- **Database Schemas**: Apply all schema alterations through Alembic migrations only. Raw SQL DDL and `create_all()` are strictly prohibited.
- **Contract Synchronization**: TypeScript response models in `libs/shared/util-types/src/lib/api-types.ts` are hand-mirrored from Pydantic schemas in `apps/hermes-api/src/hermes_api/schemas/events.py`. Update both together in the same task whenever contracts change.
- **Library Configuration IoC**: Libraries under `libs/` (`hermes-ai`, `hermes-db`, `chat`, `map`, etc.) must never read `.env` files, `os.environ`, or `import.meta.env` directly at runtime. Consumer apps (`apps/hermes`, `apps/hermes-api`, `apps/hermes-worker`) load environment variables and inject configuration/clients into library entry points (standalone CLI tools like Alembic `migrations/env.py` are the sole exception).

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

- **Production & Secret Protection**: Never run scripts/migrations against production or read full `.env.*` files. Read variable names from `.env.example` or `apps/hermes-api/.env.example` only, and verify target DB with `grep '^DB_HOST=' .env` before destructive runs. Never commit secrets or manually edit lockfiles (`package-lock.json`, `uv.lock`).
- **Mandatory Approvals**: Obtain explicit user approval before:
  1. Adding, updating, or removing dependencies (`package.json`, `pyproject.toml`).
  2. Executing database migrations (`npx nx run hermes-db:migrate`).
  3. Running `git commit` or `git push`.
- **Verification**:
  - **Read-only questions** ("how does X work?", explanations, reviews): NEVER run tests, linters, typecheckers, or `nx` commands. Read only the target file(s) and answer directly.
  - **Single-project or small edits**: Run ONLY targeted single-file checks (e.g., `npx nx test <project> -- <test_file>`, plus `lint` or `typecheck` on `<project>` if needed). Do NOT run project-wide suites or `nx affected`.
  - **Cross-package changes / pre-PR**: Run `CI=true npx nx affected -t lint typecheck test-ci --base=master` only when explicitly requested by the user.

## 6. Domain Triggers (Code Modifications Only)

Read the relevant guide **only when creating or modifying code** in that scope—skip for read-only questions:

- **React UI or routes (`apps/hermes/`, `libs/chat/`, `libs/shared/ui-components/`)**: Read `apps/hermes/AGENTS.md` and `.agents/rules/react-standards.md`.
- **Mapbox GL layers, telemetry, or clustering (`libs/map/`)**: Read `libs/map/AGENTS.md`.
- **REST endpoints or causality timelines (`apps/hermes-api/`)**: Read `apps/hermes-api/AGENTS.md`.
- **RSS/GDELT ingestion, worker, or geocoding (`apps/hermes-worker/`, `libs/shared/hermes-ai/`)**: Read `apps/hermes-worker/AGENTS.md` and `libs/shared/hermes-ai/AGENTS.md`.
- **Database schemas, models, or migrations (`libs/shared/hermes-db/`)**: Read `libs/shared/hermes-db/AGENTS.md`.
- **Any Python edit (`*.py`)**: Read `.agents/rules/python-standards.md`.
- **Any TypeScript edit (`*.ts`, `*.tsx`)**: Read `.agents/rules/ts-standards.md`.
