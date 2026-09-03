---
trigger: always_on
description: Strict rules for React, Tailwind, State Management, and TypeScript.
---

# Frontend & React Standards

- **Dumb Components / Custom Hooks**: Extract complex business logic, map state calculations, and data fetching into custom React hooks (e.g., `useMapEvents()`). UI components (returning JSX) must remain purely presentational.
- **Tailwind Exclusivity**: Use Tailwind CSS utility classes exclusively. Creating custom `.css` or `.scss` files is strictly forbidden unless absolutely necessary for complex Mapbox GL overrides. Extract reusable styles into React components rather than using `@apply`.
- **Zustand State**: NEVER mutate Zustand state directly. Strictly define and call action functions inside the store.
- **React Router Data**: Prioritize using React Router v7/v8 `loader` and `action` functions for route-level data fetching rather than triggering fetches inside `useEffect`.
- **File Naming & Casing**: Strictly use `kebab-case.tsx` for all React files (e.g., `event-marker.tsx`). Use `camelCase` for naming variables, functions, and filenames in the JS/TS ecosystem.
- **Props**: ALWAYS destructure React props in the function signature (e.g., `function Map({ data }):`) rather than accessing them via `props.data`.
- **Exhaustive Deps**: Strictly follow React's `exhaustive-deps` rule. NEVER suppress the eslint warning (`// eslint-disable-next-line`) to make a bug go away.
- **TypeScript Strictness**: 
  - NEVER use the `any` type. If unknown, use `unknown` and type-guard it.
  - Strictly use `interface` instead of `type` for object definitions (unless defining unions/intersections).
  - Use absolute path aliases (e.g., `import { Button } from '@hermes/ui'`) and avoid deep relative paths.
- **Testing**: Explicitly write Playwright E2E tests for the most critical user journeys.
