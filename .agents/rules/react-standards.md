---
trigger: glob
description: Strict React 19 standards, React Router v8 architecture, directory conventions, shadcn and Tailwind v4 integration, hooks hygiene, and state architecture.
globs: '**/*.tsx, **/use-*.ts, **/use*.ts, **/react-router.config.ts, **/routes.tsx'
---

# React & React Router Standards

## Architecture & Routing

- **Thin Route Shells**: Route modules in `apps/hermes/app/routes/` handle metadata (`meta`), loaders, `ErrorBoundary`, and layout composition only. Keep business logic, stores, and widgets in `libs/`.
- **Explicit Props & Pure Render**: Define an explicit `interface <ComponentName>Props` for every component accepting props. Never mutate external state or trigger side effects in the render body.

## React 19 & Effects Hygiene

- **Direct `ref` Prop**: Pass `ref` directly as a prop (`React.forwardRef` is deprecated and forbidden).
- **Modern Hooks**: Use `useTransition`, `useActionState`, `useOptimistic`, and `use(Context)` instead of manual loading-flag state soup or `useContext`.
- **Minimal `useEffect`**: Never use `useEffect` for derived state (compute inline during render), user event responses (use event handlers), or resetting state on prop changes (pass a `key` prop). Reserve `useEffect` strictly for external sync (Mapbox, DOM listeners, observers) with mandatory cleanup.

## 6-Tier State Hierarchy (No Shadow State)

1. **URL State** (`useSearchParams`, `useParams`): Shareable view filters/selections.
2. **Server State** (TanStack Query): Remote API data and caching.
3. **Global Telemetry** (Zustand `useMapStore`): Real-time cross-widget state via atomic selectors.
4. **Local UI State** (`useState` / `useReducer`): Component-scoped toggles.
5. **Derived State**: Inline render calculation (`useMemo` only if profiled expensive).
6. **Transient Values** (`useRef`): Non-rendering instances, timers, animation refs.

## Mapbox GL Isolation

- **Mapbox Ref Rule**: Always store the `mapboxgl.Map` instance in `useRef<mapboxgl.Map | null>(null)`—never in `useState`. Treat Mapbox as a pure rendering sink driven by `useMapStore`.
