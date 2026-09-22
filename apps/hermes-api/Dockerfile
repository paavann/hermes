FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-install-project

COPY . .

RUN uv sync --locked

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn hermes_api.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info"]