FROM python:3.14-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY libs/shared/hermes-db/pyproject.toml libs/shared/hermes-db/
COPY apps/hermes-api/pyproject.toml ./apps/hermes-api/

# development target (includes dev tools, uvicorn with hot reload).
FROM base AS development
RUN uv sync --package hermes-api --frozen --no-install-project
COPY libs/shared/hermes-db ./libs/shared/hermes-db
COPY apps/hermes-api ./apps/hermes-api
RUN uv sync --package hermes-api --frozen
WORKDIR /app/apps/hermes-api
ENV PORT=8000
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "hermes_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# production target (--no-dev, precompiled bytecode, production worker pool).
FROM base AS production
ENV UV_COMPILE_BYTECODE=1
RUN uv sync --package hermes-api --frozen --no-dev --no-install-project
COPY libs/shared/hermes-db ./libs/shared/hermes-db
COPY apps/hermes-api ./apps/hermes-api
RUN uv sync --package hermes-api --frozen --no-dev
WORKDIR /app/apps/hermes-api
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn hermes_api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
