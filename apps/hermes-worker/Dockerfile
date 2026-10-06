FROM python:3.14-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY libs/shared/hermes-db/pyproject.toml libs/shared/hermes-db/
COPY apps/hermes-api/pyproject.toml ./apps/hermes-api/
COPY apps/hermes-worker/pyproject.toml ./apps/hermes-worker/

# development target (includes dev tools).
FROM base AS development
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package hermes-worker --frozen --no-install-workspace
COPY libs/shared/hermes-db ./libs/shared/hermes-db
COPY apps/hermes-worker ./apps/hermes-worker
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package hermes-worker --frozen
WORKDIR /app/apps/hermes-worker
ENTRYPOINT ["uv", "run", "python", "-m", "hermes_worker.cli"]
CMD ["run-all"]

# production target (--no-dev, precompiled bytecode).
FROM base AS production
ENV UV_COMPILE_BYTECODE=1
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package hermes-worker --frozen --no-dev --no-install-workspace
COPY libs/shared/hermes-db ./libs/shared/hermes-db
COPY apps/hermes-worker ./apps/hermes-worker
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package hermes-worker --frozen --no-dev
WORKDIR /app/apps/hermes-worker
ENTRYPOINT ["uv", "run", "python", "-m", "hermes_worker.cli"]
CMD ["run-all"]
