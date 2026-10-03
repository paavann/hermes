---
trigger: always_on
---

# Python Standards

## Coding Style & Conventions

- **Strict Type Hinting**: ALWAYS add explicit Python type hints for EVERY function argument and return type. Untyped functions are strictly forbidden. Use `snake_case` for Python variables and functions.
- **Strict Enum Usage**: ALWAYS use Python `enum.Enum` (specifically `(str, enum.Enum)`) wherever appropriate when handling a fixed set of status, scope, type, category, or tier values. Hardcoding raw string literals across services, models, schemas, or status updates is strictly forbidden.
- **Python Imports**: Strictly use absolute imports in Python (e.g., `from src.services.db import get_db`) and avoid relative dot imports.
- **Minimal Naming Conventions**: The naming of variables, functions, and other identifiers should be kept minimal and short. Use concise forms to keep the code clean.
- **Pragmatic DRY Principle**: Strictly follow and adhere to DRY (Don't Repeat Yourself) principles while writing code wherever possible, but avoid applying it in situations where it adds unnecessary complexity or seems not required.

## Tooling, Logging & Documentation

- **Ruff Exclusivity**: Strictly adhere to the `ruff` configuration in `pyproject.toml`. Do not introduce `black`, `flake8`, or `isort`.
- **Parameterized Logging**: ALWAYS use parameterized string formatting (e.g., `logger.info("Message %s", var)` or `logger.exception("Failed %s", var)`) across all logger levels (`debug`, `info`, `warning`, `error`, `exception`). Using f-strings or `.format()` inside logger calls is strictly forbidden to preserve deferred evaluation, performance short-circuiting, and structured log aggregation.
- **Developer Log Formatting**: All internal developer log messages (which are for internal observability and never sent to API clients) MUST start with a lowercase letter (never capitalized) and MUST always end with a period (`.`). If a log message consists of multiple sentences, periods must be included in-between sentences as well (e.g., `logger.info("fetching event %s. timeline generation starting.", event_id)`).
- **Documentation**: Write Google-style docstrings for all Python service functions and complex endpoints.
