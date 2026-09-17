FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-install-project

COPY . .

RUN uv sync --locked

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "hermes_api.main:app", "--host", "[IP_ADDRESS]", "--port", "8000", "--log-level", "warning"]