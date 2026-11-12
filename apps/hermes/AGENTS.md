# Hermes Application (`apps/hermes`)

Routing and top-level provider composition shell for the Hermes frontend.

## 1. Commands

Run all commands from the workspace root using project `@hermes/hermes`. See root `AGENTS.md` Commands table for dev, lint, typecheck, test, and format.

| Task      | Command                       |
| :-------- | :---------------------------- |
| **Build** | `npx nx build @hermes/hermes` |

## 2. Invariants

- **Server-Side Access Control**: Enforce route access control server-side in loaders using `getAuth` (Clerk). Never gate protected routes or sensitive data exclusively in client components.
- **Zero Border Radius & Design Tokens**: Never use `rounded-*` utility classes. Consume semantic tokens from `apps/hermes/styles.css` instead of hardcoding colors or typography.
- **Clerk Proxy Route**: Keep Clerk proxy handling isolated in `app/routes/clerk-proxy.ts`; do not bypass or duplicate proxy configuration in individual route loaders.

## 3. Domain Triggers (Code Modifications Only)

- **When adding/changing auth flows, route loaders, or SSR config**: Read `apps/hermes/docs/architecture.md`.
- **When modifying map state, WebGL layers, or clustering**: Read `libs/map/AGENTS.md`.
