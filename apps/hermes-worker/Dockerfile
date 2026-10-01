FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY libs/shared/hermes-db ./libs/shared/hermes-db
COPY apps/hermes-worker/pyproject.toml apps/hermes-worker/uv.lock ./apps/hermes-worker/

WORKDIR /app/apps/hermes-worker

RUN uv sync --locked --no-install-project

COPY apps/hermes-worker .

RUN uv sync --locked

ENTRYPOINT ["uv", "run", "python", "-m", "hermes_worker.cli"]
CMD ["run-all"]
