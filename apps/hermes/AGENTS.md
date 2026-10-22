# Hermes Application (`apps/hermes`)

Routing and top-level provider composition shell for the Hermes frontend.

## 1. Commands

Run all commands from the workspace root using project `@hermes/hermes`. See root `AGENTS.md` Commands table for dev, lint, typecheck, test, and format.

| Task      | Command                       |
| :-------- | :---------------------------- |
| **Build** | `npx nx build @hermes/hermes` |

## 2. Invariants

- **Server-Side Access Control**: Enforce route access control server-side in loaders using `getAuth`. Do not gate protected routes or sensitive data exclusively in client components.
- **Client-Only Mapbox Rendering**: Mapbox GL requires browser APIs (`window`, WebGL) and fails during SSR (`ssr: true`). Isolate all Mapbox imports behind dynamic `React.lazy` boundaries with `Suspense` and a fallback skeleton.
- **Shared UI Primitives**: Build reusable UI components in `libs/shared/ui-components` before consuming them here; never define base primitives in `apps/hermes`.
- **Zero Border Radius & Tokens**: Never use `rounded-*` utility classes. Consume semantic design tokens from `apps/hermes/styles.css` instead of hardcoding colors or typography.

## 3. Domain Triggers

- **When modifying authentication, route loaders, SSR, or layout**: Read `apps/hermes/docs/architecture.md`.
- **When modifying map state, WebGL layers, or clustering**: Read `libs/map/AGENTS.md`.
