FROM python:3.14-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY libs/shared/hermes-db/pyproject.toml libs/shared/hermes-db/
COPY apps/hermes-worker/pyproject.toml ./apps/hermes-worker/

# development target (includes dev tools).
FROM base AS development
RUN uv sync --package hermes-worker --frozen --no-install-project
COPY libs/shared/hermes-db ./libs/shared/hermes-db
COPY apps/hermes-worker ./apps/hermes-worker
RUN uv sync --package hermes-worker --frozen
WORKDIR /app/apps/hermes-worker
ENTRYPOINT ["uv", "run", "python", "-m", "hermes_worker.cli"]
CMD ["run-all"]

# production target (--no-dev, precompiled bytecode).
FROM base AS production
ENV UV_COMPILE_BYTECODE=1
RUN uv sync --package hermes-worker --frozen --no-dev --no-install-project
COPY libs/shared/hermes-db ./libs/shared/hermes-db
COPY apps/hermes-worker ./apps/hermes-worker
RUN uv sync --package hermes-worker --frozen --no-dev
WORKDIR /app/apps/hermes-worker
ENTRYPOINT ["uv", "run", "python", "-m", "hermes_worker.cli"]
CMD ["run-all"]
