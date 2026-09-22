# Hermes Frontend — AI Agent Context

This document provides frontend-specific architectural context for the `hermes` React application. It is scoped to this directory and supplements the root `AGENTS.md`.

---

## 1. Application Role

This is the **frontend shell** of Project Hermes. It is a React application built with **React 19**, **React Router 8** (SPA mode via Vite), **Tailwind CSS 4**, **Zustand 5**, **TanStack React Query v5**, and **Mapbox GL JS v3**. Its primary job is to render an interactive geospatial map and tactical "Mission Control" UI overlays for users to observe global news events.

As a thin `apps/` shell in the Nx monorepo:
- `apps/hermes` contains **only** route definitions, layout providers, and application configuration.
- Reusable UI widgets live in `libs/shared/ui-components` (`BootSequence`, `LiveClock`).
- Map engine, layers, custom projection hooks, and map state live in `libs/feature-map` (`MapView`, `EventPopup`, `TlPanel`, `useMapStore`).
- Shared TypeScript API interfaces live in `libs/shared/util-types` (`MapEventResponse`, `EventDetailResponse`, `TlResponse`).

---

## 2. UI/UX Design Language

### Theme & Visual Identity ("Mission Control")

- **Theme**: "Mission Control" — a tech-forward, high-density aesthetic inspired by military tactical command centers and financial terminals.
- **Dark Mode**: Strictly dark-themed (`#050505` background, slate text).
- **Glassmorphism**: Floating panels use translucent backgrounds with `backdrop-blur-md` (`bg-hud-bg/95`) and glowing tactical borders (`border border-hud-border`).
- **Sharp Edges (Zero Border Radius)**: All cards, modals, buttons, badges, and popups must have **zero border-radius** (completely squared, sharp-edged). This is strictly enforced in `tailwind.config.js` via `corePlugins: { borderRadius: false }`. Rounded corners are strictly forbidden.
- **Typography**: Strictly monospaced (`"JetBrains Mono"`, `"Fira Code"`, monospace) to maintain columnar alignment and telemetry precision.
- **Single Page Application**: Configured with `ssr: false` in `react-router.config.ts` because Mapbox GL relies entirely on client-side WebGL canvas and `window`.

### Color System & Tactical Tokens

Defined in `tailwind.config.js`:
- `hud-bg`: `rgba(10, 15, 25, 0.85)` (deep semi-transparent tactical navy)
- `hud-border`: `#1e3a8a` (dark military blue border)
- `hud-glow`: `#3b82f6` (neon electric blue glow)
- `neon-blue`: `#00f0ff` (cyberpunk bright cyan)
- `warning-yellow`: `#fbbf24` (alert highlight yellow)

### Core Presentation Components

- **`BootSequence`** (`libs/shared/ui-components`): Terminal startup sequence displaying ASCII logo, simulated satellite handshake, and system integrity checks before revealing the map.
- **`LiveClock`** (`libs/shared/ui-components`): Real-time dual UTC and Local digital clock with a blinking heartbeat monitor in the top-right corner.
- **`EventPopup`** (`libs/feature-map`): Floating HUD window that tracks geographic coordinates via `requestAnimationFrame` projection calculations (`map.project()`). Features an automatic text-scrambler decode effect on AI summaries and links to original sources.
- **`TlPanel`** (`libs/feature-map`): Slide-out intelligence dossier rendering historical causal events, Wikipedia context, and interactive map camera hops to historical sub-event coordinates.

---

## 3. State Management Architecture

### Zustand as Single Source of Truth

- **Zustand** (`useMapStore` in `libs/feature-map/src/lib/store/store.ts`) is the global map store.
- **State Properties**:
  - `selectedEventId`: UUID string of the actively selected event (or `null`).
  - `selectedEventLngLat`: `[longitude, latitude]` of the active event.
  - `viewport`: Current geographic bounding box (`north`, `south`, `east`, `west`).
  - `isTlMode`: Boolean flag indicating if historical timeline mode is active.
  - `tlTargetId`: Event ID whose timeline is currently being inspected.
- Both the Mapbox GL instance and React HUD overlays react to and update the same Zustand store. Never allow the Mapbox map instance to maintain shadow state that React cannot observe.

### Data Flow Pattern

1. **User pans/zooms the map** &rarr; Mapbox `moveend` updates `viewport` in Zustand.
2. **`useMapDataSync` (TanStack Query)** observes `viewport` &rarr; fires a debounced API request to `/api/v1/events/bbox?north=..&south=..&east=..&west=..`.
3. **Client GeoJSON Transformation**: Since the backend returns `MapEventResponse[]`, `createGeoJson()` deduplicates coordinates and constructs a GeoJSON `FeatureCollection` with ranked properties (`rank: 1, 2, 3...`).
4. **Mapbox GeoJSON Source** updates `events-source` &rarr; WebGL pipeline updates markers natively.
5. **Marker Selection**: Clicking an unclustered marker writes `selectedEventId` and coordinates to Zustand, centers the camera smoothly with `easeTo`, and displays `EventPopup`.

---

## 4. Map Rendering & WebGL Performance

### Mapbox Native Layers (Critical Rule)

All event pins, clusters, and relationship lines must be rendered using **Mapbox GL native layers** fed by GeoJSON sources (`map.addSource` and `map.addLayer`). **HTML DOM markers (`new mapboxgl.Marker()`) are strictly forbidden** for event pins because rendering thousands of DOM elements destroys browser performance.

### Visualization Layers

1. **`events-source`**: Native GeoJSON source with clustering enabled (`clusterMaxZoom: 14`, `clusterRadius: 50`).
2. **`hermes-clusters`**: Circle layer for dense marker clusters. Uses step expressions to become transparent at zoom &ge; 8 with hollow borders.
3. **`hermes-cluster-count`**: Symbol layer rendering `point_count_abbreviated` in JetBrains Mono.
4. **`hermes-unclustered-point`**: Circle layer for individual breaking news pins. Data-driven styled by `category_color` and rank-based radius (`[1, 18, 2, 14, 3, 10, 6]`).
5. **`tl-edges-layer`**: Dashed cyan line layer (`#00f0ff`, `line-width: 2`, `line-dasharray: [2, 2]`) connecting causal historical timeline nodes.
6. **`tl-nodes-layer`**: Circle layer for historical timeline nodes with category colors and halo outlines.

### Camera Interactions

- **Robotic Cluster Zoom**: Clicking a cluster calculates the expansion zoom and executes a pure linear easing transition (`easing: (t) => t`) for a responsive tactical feel.
- **Event Pin Selection**: Clicking a pin pans the camera smoothly to center the popup (`easeTo` with quadratic ease-out).

---

## 5. Server State & Timeline Polling

- **TanStack Query v5**: Handles all HTTP fetching and caching:
  - `useMapDataSync`: 5-second `staleTime` for viewport data.
  - `useEventDetails`: 60-second `staleTime` for event summaries and source articles.
  - `useTl`: Initiates historical timeline generation. If `query.state.data?.status === 'GENERATING'`, automatically sets `refetchInterval: 3000` to poll until graph synthesis completes.

---

## 6. Accessibility (a11y)

- **Pragmatic Accessibility**: All UI elements **outside the map** (sidebars, timeline panels, popups, buttons) must support keyboard navigation (`Tab`, `Enter`, `Escape`), proper ARIA labels, and high contrast against dark backgrounds.
- **Map Canvas**: The WebGL canvas is recognized as visually dependent. Individual WebGL markers are not exposed to screen readers; the drawer panels provide accessible textual alternatives.
