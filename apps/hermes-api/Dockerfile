FROM python:3.14-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY libs/shared/hermes-db/pyproject.toml libs/shared/hermes-db/
COPY libs/shared/hermes-ai/pyproject.toml libs/shared/hermes-ai/
COPY apps/hermes-api/pyproject.toml ./apps/hermes-api/
COPY apps/hermes-worker/pyproject.toml ./apps/hermes-worker/

# development target (includes dev tools, uvicorn with hot reload).
FROM base AS development
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package hermes-api --frozen --no-install-workspace
COPY libs/shared/hermes-db ./libs/shared/hermes-db
COPY libs/shared/hermes-ai ./libs/shared/hermes-ai
COPY apps/hermes-api ./apps/hermes-api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package hermes-api --frozen
WORKDIR /app/apps/hermes-api
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uv run alembic -c ../../libs/shared/hermes-db/alembic.ini upgrade head && uv run uvicorn hermes_api.main:app --host 0.0.0.0 --port 8000 --reload"]

# production target (--no-dev, precompiled bytecode, production worker pool).
FROM base AS production
ENV UV_COMPILE_BYTECODE=1
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package hermes-api --frozen --no-dev --no-install-workspace
COPY libs/shared/hermes-db ./libs/shared/hermes-db
COPY libs/shared/hermes-ai ./libs/shared/hermes-ai
COPY apps/hermes-api ./apps/hermes-api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package hermes-api --frozen --no-dev
WORKDIR /app/apps/hermes-api
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uv run alembic -c ../../libs/shared/hermes-db/alembic.ini upgrade head && uv run uvicorn hermes_api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
