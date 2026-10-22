# Hermes Map (`libs/map`)

Mapbox GL JS WebGL map engine, spatial queries, and timeline visualization library.

## 1. Commands

Run commands from the workspace root using project `@hermes/map`. See root `AGENTS.md` Commands table for syntax.

| Task          | Command                        |
| :------------ | :----------------------------- |
| **Lint**      | `npx nx lint @hermes/map`      |
| **Typecheck** | `npx nx typecheck @hermes/map` |
| **Test**      | `npx nx test @hermes/map`      |

## 2. Invariants

- **Store Authority**: `useMapStore` is the single source of truth for viewport bounding box (`viewport`), event selection (`selectedEventId`, `selectedEventLngLat`), and timeline inspection mode (`isTlMode`, `tlTargetId`).
- **Map Instance Storage**: Store `mapboxgl.Map` exclusively in `useRef<mapboxgl.Map | null>(null)`. Never store it in React `useState`.
- **Pure Rendering Sink**: The `mapboxgl.Map` instance is a pure rendering sink; never maintain internal map state that diverges from `useMapStore`. User map interactions dispatch directly into the store.
- **GPU Canvas Rendering**: Render clustered nodes and unclustered pins directly via WebGL canvas layers (`circle` and `symbol` layers in Mapbox). Never mount HTML DOM marker nodes (`new mapboxgl.Marker()`).
- **Decoupled Configuration**: Supply credentials and endpoints via `<MapConfigProvider>`; never access `process.env` or `import.meta.env` directly within `libs/map`.
- **Declarative Synchronization**: `useMapDataSync` observes the store's `viewport` and updates map GeoJSON sources without cyclical re-renders.

## 3. Domain Triggers

- **When editing Mapbox GL layers, shaders, or GIS styling**: Read `libs/map/standards.md`.
- **When modifying map architecture, debouncing, or camera physics**: Read `libs/map/docs/architecture.md`.
