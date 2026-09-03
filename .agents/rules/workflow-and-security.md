---
trigger: always_on
description: Strict rules for Nx workflow, Git, and Security.
---

# Workflow & Security Standards

- **Absolute Secrecy**: Strictly forbidden from hardcoding, logging, or printing any API keys. Must fetch via `pydantic-settings` or `import.meta.env`.
- **No Silent Defaults**: NEVER provide fallback defaults for critical environment variables (like API keys) in `pydantic-settings`. Force a crash if missing.
- **Nx Dependency Management**: Strictly use Nx scripts (defined in `project.json`) to manage backend dependencies. If a script for core functionality is absent, notify the user.
- **Conventional Commits**: Strictly use Conventional Commits format (e.g., `feat(map): add marker clustering`) with extensive descriptions when proposing commits.

# Documentation & Verification Standards

- **Mandatory Documentation Verification**: Before implementing any change involving a specific library (React Router, FastAPI, Mapbox GL, GeoAlchemy2, etc.), ALWAYS use web search or specialized skills to read the **latest official documentation** for that exact version. Do NOT rely on general training data — APIs change between versions.
- **Dependency File Inspection**: Before starting any task, ALWAYS check `package.json`, `nx.json`, `pyproject.toml`, and relevant config files to verify the **current versions** of all tools and libraries being used. Base all implementation decisions on what is actually installed, not what you assume.
- **Respect Existing Formatting**: Respect the existing Prettier and ESLint configurations. Do NOT reformat code outside of the lines you are actively editing. Unnecessary formatting changes create noisy diffs and obscure real changes in code review.
