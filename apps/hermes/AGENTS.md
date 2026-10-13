# Hermes Frontend (`apps/hermes`) — AI Agent Context & Brain

This document provides high-level architectural context, constraints, and engineering decisions specific to the frontend shell in `apps/hermes`. All AI agents contributing to this module must adhere to the principles outlined below.

---

## 1. Module Role & The 80/20 Monorepo Boundary

`apps/hermes` is an ultra-thin configuration and routing shell. In accordance with the Nx monorepo **80/20 rule**:
- **What belongs here (<20%)**: Route configuration (`app/routes.tsx`), root HTML/document shell (`app/root.tsx`), top-level provider tree assembly (`app/app.tsx`), build toolchain (`vite.config.mts`, `react-router.config.ts`), and environment binding.
- **What is strictly forbidden here (>80%)**: Business logic, spatial queries, Mapbox layer configurations, raw WebGL operations, and reusable UI widgets. These must reside in dedicated libraries:
  - Geospatial visualization, clustering, timeline drawer, and telemetry store: [`libs/map`](file:///home/pavan/proj/hermes/libs/map)
  - Mission Control HUD widgets (`BootSequence`, `LiveClock`): [`libs/shared/ui-components`](file:///home/pavan/proj/hermes/libs/shared/ui-components)
  - Shared TypeScript data contracts: [`libs/shared/util-types`](file:///home/pavan/proj/hermes/libs/shared/util-types)

**Engineering Tradeoff**: Isolating the shell prevents framework coupling, ensures high component reusability (e.g., E2E harnesses, potential embedded views), and enforces strict Nx architectural boundaries (`type:app`, `scope:frontend`).

---

## 2. Architectural Rationale: Strict SPA Mode (`ssr: false`)

The application is explicitly configured for Single Page Application mode via `ssr: false` in [`react-router.config.ts`](file:///home/pavan/proj/hermes/apps/hermes/react-router.config.ts).

### Why SSR Was Rejected
1. **WebGL Canvas Hydration Impossibility**: The core Hermes interface is driven by Mapbox GL JS v3, which requires a live `window` reference, direct DOM measurements, and an active `WebGLRenderingContext`. A server-side streaming or pre-rendering pass cannot construct or hydrate a WebGL canvas context.
2. **Hydration Mismatches & Double Mounting**: Attempting SSR for map-heavy pages produces hydration mismatches, awkward DOM flashing, or forced two-phase mounting shields that introduce unnecessary latency.
3. **Domain Applicability**: Hermes is an interactive, real-time tactical command console rather than a text-heavy, indexable blog. SEO crawlers do not index real-time WebGL canvas frames.

**Implementation**: Vite builds a minimal HTML host document (`build/client/index.html`) that boots React 19 directly in the client browser, completely eliminating SSR overhead while maximizing runtime stability.

---

## 3. Telemetry & Unidirectional Data Flow (No Shadow State)

State and telemetry flow strictly unidirectionally across three synchronized layers:

```
Mapbox GL Canvas (Pan/Zoom/Click)
        │ (Dispatches raw map events)
        ▼
Zustand Store (`useMapStore` in libs/map)  ◄── Single Source of Truth
        │ (Observes viewport bbox)
        ▼
TanStack Query (`useMapDataSync` in libs/map)
        │ (HTTP GET /api/v1/events/bbox)
        ▼
Backend REST API (`hermes-api`)
        │ (GeoJSON FeatureCollection transformation)
        ▼
Mapbox GL Native Layers (GeoJSON Source Update)
```

### Strict State Rules
- **Single Source of Truth**: [`useMapStore`](file:///home/pavan/proj/hermes/libs/map/src/lib/store/store.ts) is the sole authority for viewport bounding boxes (`north`, `south`, `east`, `west`), active event selection (`selectedEventId`), and timeline drawer mode (`isTlMode`).
- **No Mapbox Shadow State**: The Mapbox GL JS map instance is strictly a rendering sink. It must **never** maintain internal state that diverges from Zustand. User panning/zooming dispatches directly into `useMapStore.setViewport`.
- **Declarative Query Sync**: TanStack Query (`useQuery`) observes the Zustand `viewport` key, executing debounced spatial bbox fetches against `hermes-api`. When responses arrive, GeoJSON data is pushed cleanly to Mapbox native sources without cyclical re-renders.

---

## 4. Pragmatic Accessibility (a11y) Boundaries

Because Mapbox renders pins onto a hardware-accelerated WebGL `<canvas>`, individual map markers are not distinct DOM elements:
- **Canvas Rule**: Do NOT attempt to mount thousands of hidden off-screen DOM nodes to represent geospatial map pins. Doing so causes severe DOM bloat, breaks 60 FPS canvas performance, and creates an unusable screen-reader experience.
- **HUD & Overlay Rule**: All standard HTML DOM elements—including tactical HUD overlays, modal dialogs, the timeline drawer (`TlPanel`), and event inspection popups (`EventPopup`)—must maintain strict semantic markup, keyboard navigability (`Escape` dismissal, focus trapping), and descriptive ARIA roles.
- **Information Parity**: Assistive tech users inspect event details, causality timelines, and source citations via the accessible overlay panels rather than raw canvas markers.

---

## 5. Design System: Mission Control Constraints

The UI enforces a strict tactical command center aesthetic configured via Tailwind CSS 4:
- **Zero Border Radius**: Globally enforced via `corePlugins: { borderRadius: false }` in [`tailwind.config.js`](file:///home/pavan/proj/hermes/apps/hermes/tailwind.config.js). Rounded corners (`rounded-*`) are strictly disallowed.
- **Monospace Typography**: `JetBrains Mono` and `Fira Code` are applied across all text elements (`font-mono`, `font-sans`).
- **Tactical Palette**: Cyberpunk/tactical accents (`hud-bg`, `hud-border: #1e3a8a`, `hud-glow: #3b82f6`, `neon-blue: #00f0ff`, `warning-yellow: #fbbf24`).
