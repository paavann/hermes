---
trigger: glob
globs: **/*.py
---

# Python Standards

## Coding Style & Conventions

- **Strict Type Hinting & No `Any`**: Add explicit type hints for every function/method parameter and return type. Using `Any` is forbidden—use concrete types, Pydantic models, `TypedDict`, generics, or `object` with type guards.
- **Strict Enum Usage**: Use `(str, enum.Enum)` for fixed sets of statuses, scopes, tiers, or categories. Never hardcode raw status string literals.
- **Absolute Imports Only**: Use absolute imports (e.g., `from hermes_api.services.db import get_db`); avoid relative dot imports.
- **Concise Naming & No Aliasing**: Keep variable and function names concise (`snake_case`). Never define method or function aliases (e.g., `call = call_llm`); invoke every symbol by its single canonical name.
- **Configuration via Pydantic Settings**: Never call `os.environ` or `os.getenv` in application services, handlers, or CLI commands. Declare and validate env vars via typed `pydantic_settings.BaseSettings` in `core/config.py` (shared libraries under `libs/` must never read env vars directly; receive config via explicit parameters).

## Tooling & Logging

- **Ruff Exclusivity**: Follow the `ruff` configuration in `pyproject.toml`. Do not introduce `black`, `flake8`, or `isort`.
- **Parameterized Logging**: Always use `%s`-style parameterized formatting (`logger.info("fetching event %s.", event_id)`), never f-strings or `.format()`.
- **Developer Log Formatting**: Internal developer log messages must start with a lowercase letter and end with a period (`.`), including periods between multiple sentences.
