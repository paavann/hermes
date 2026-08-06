---
trigger: always_on
description: Core development standards and project context for Hermes.
---

# Project Context & Intent

- The Core vision: Hermes is a Real-Time Geospatial News Aggregator. The core idea is to combat modern "news fatigue" and geopolitical opacity by transforming endless, text-heavy news feeds into a unified, interactive global map. Instead of reading about events happening around the world, users observe them unfolding on a geographic canvas. By leveraging AI to extract the exact physical locations of events and visualizing them through color-coded markers, shaded territories, and connection arcs, Hermes makes complex geopolitical and economic relationships instantly digestible.

# 1. Documentation & Dependency Verification

- Before implementing any change, ALWAYS check `package.json`, `nx.json`, `pyproject.toml` and various other dependency files in a directory to verify the current versions of all tools and libraries being used.
- If you are working with a specific tool (e.g., React Router 7, FastAPI), you MUST use web search or your specialized skills to read the latest official documentation for that exact version before writing code.
- Base all architectural decisions and code implementations on the official documentation rather than general training data.

# 2. Nx Monorepo Workflow

- This is an Nx monorepo. ALWAYS use `nx` commands instead of standard `npm` commands.
- Use commands like `npx nx serve <app>`, `npx nx build <app>`, and `npx nx test <app>`.
- To discover available scripts, targets, and configurations for a specific project, inspect the project.json (or local configuration files) located inside that project's directory within the apps/ or packages/ folder.
- Do NOT navigate into child directories (e.g., `cd apps/hermes`) to run scripts. Run all commands from the root directory using Nx.

# 3. Tech Stack Specifics

- **Python Dependencies**: Strictly use `uv` for managing Python dependencies in the backend.

# 4. Code Quality & Formatting

- **TypeScript Strictness**: Always use explicit types in the frontend. Do not use `any`. Define proper interfaces for all API responses and payloads.
- **Formatting**: Respect the existing Prettier and ESLint configurations. Do not reformat code unnecessarily.

# 5. Architecture & Best Practices

- **React**: Favor small, reusable functional components. Keep business logic out of UI components by extracting it into custom hooks.
- **FastAPI**: Keep API route handlers thin. Delegate database calls and complex business logic to a separate `services/` layer.
- **Error Handling**: Use React Error Boundaries on the frontend. On the backend, gracefully handle failures by raising structured `HTTPException`s.

# 6. Security & Secrets

- **No Hardcoding**: NEVER hardcode API keys, database credentials, or secret tokens. Always read from environment variables.
