# Hermes Frontend — AI Agent Context

## 1. Application Role & Boundary
`apps/hermes` is a thin configuration shell. It contains **only** route definitions, layout providers, and environment configuration. All business logic, map state, and reusable UI components must reside in `libs/map` or `libs/shared/ui-components`.

## 2. SPA Mode Rationale
The application is explicitly configured for Single Page Application (SPA) mode (`ssr: false` in `react-router.config.ts`). Server-Side Rendering is disabled because the core experience relies on Mapbox GL JS, which requires `window` and a WebGL canvas context that cannot be hydrated safely from a server stream.

## 3. State & Data Flow Pipeline
The architecture relies on a strict unidirectional data flow:
1. **Zustand (`useMapStore`)**: The absolute single source of truth for viewport coordinates and selection state.
2. **TanStack Query (`useMapDataSync`)**: Observes Zustand's `viewport` and fires debounced spatial bounding-box API requests.
3. **GeoJSON Transformation**: API responses are mapped into a client-side GeoJSON `FeatureCollection`.
4. **Mapbox Native Engine**: The GeoJSON feeds directly into Mapbox native WebGL layers. The Mapbox instance must NEVER hold shadow state independent of Zustand.

## 4. Pragmatic Accessibility (a11y)
While HTML UI elements (drawers, buttons, HUD overlays) must support strict keyboard navigation and ARIA labels, the Mapbox WebGL canvas is inherently visually dependent. Do not attempt to mount thousands of hidden DOM nodes to make map pins screen-reader accessible; instead, rely on the supplementary UI panels to expose data.
