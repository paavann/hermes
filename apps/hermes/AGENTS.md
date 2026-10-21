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

## 2. Architectural Rationale: Server-Side Rendering (`ssr: true`) with Dynamic WebGL Isolation

The application runs in Server-Side Rendering (SSR) mode via `ssr: true` in [`react-router.config.ts`](file:///home/pavan/proj/hermes/apps/hermes/react-router.config.ts).

### Why SSR and How WebGL Canvas Is Isolated
1. **Server Authentication Guarding**: In SSR mode, Clerk runs [`clerkMiddleware()`](file:///home/pavan/proj/hermes/apps/hermes/app/root.tsx) and [`rootAuthLoader()`](file:///home/pavan/proj/hermes/apps/hermes/app/root.tsx) to verify session JWT cookies directly in Node.js, completely eliminating unauthenticated UI flashing on initial document requests. Route loaders enforce access via `getAuth(args)`.
2. **Client-Only WebGL Boundary**: Because Mapbox GL JS v3 requires a live `window` reference, direct DOM measurements, and an active `WebGLRenderingContext`, it is strictly isolated behind a dynamic `React.lazy` boundary in [`apps/hermes/app/routes/map.tsx`](file:///home/pavan/proj/hermes/apps/hermes/app/routes/map.tsx). During SSR, Node.js renders a lightweight tactical loading fallback (`MapLoadingFallback`), preventing any WebGL or `window` evaluation errors on the server.
3. **Hydration Parity**: Server-rendered HTML delivers the core document shell, metadata, and tactical layouts while Mapbox GL initializes smoothly upon client hydration.

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
- **Zero Border Radius**: Globally enforced via `--radius-*: initial;` inside `@theme` in [`styles.css`](file:///home/pavan/proj/hermes/apps/hermes/styles.css). Rounded corners (`rounded-*`) are strictly disallowed and purged from the utility scale.
- **Monospace Typography**: `JetBrains Mono` and `Fira Code` are applied across all text elements (`font-mono`, `font-sans`).
- **Tactical Palette**: Cyberpunk/tactical accents (`hud-bg`, `hud-border: #1e3a8a`, `hud-glow: #3b82f6`, `neon-blue: #00f0ff`, `warning-yellow: #fbbf24`).

---

## 6. Official Rules & Coding Standards

All AI agents contributing React and TypeScript code to this module must strictly adhere to the project standards:
- [`.agents/rules/react-standards.md`](file:///home/pavan/proj/hermes/.agents/rules/react-standards.md) — React 19, React Router v8, component architecture, hooks hygiene, 6-tier state hierarchy, and UI guidelines.
- [`.agents/rules/ts-standards.md`](file:///home/pavan/proj/hermes/.agents/rules/ts-standards.md) — Compile-time TypeScript safety, import discipline, and naming conventions.
- [`.agents/rules/mapbox-gis.md`](file:///home/pavan/proj/hermes/.agents/rules/mapbox-gis.md) — Mapbox GL WebGL performance and data-driven styling.
