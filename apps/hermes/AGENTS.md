# Hermes Frontend — AI Agent Context

This document provides frontend-specific architectural context for the `hermes` React application. It is scoped to this directory and supplements the root `AGENTS.md`.

---

## 1. Application Role

This is the **frontend shell** of Project Hermes. It is a React application built with React Router 7, Vite, and Tailwind CSS. Its primary job is to render an interactive geospatial map (via Mapbox GL JS) and provide UI overlays (sidebars, filters, panels) for users to explore global news events visually.

As a thin `apps/` shell in the Nx monorepo, this application should contain **only** route definitions, layout components, and application-level configuration. All reusable UI components, business logic hooks, and API utilities must live in shared `libs/` libraries.

---

## 2. UI/UX Design Language

### Theme & Visual Identity
- **Theme**: "Mission Control" — a tech-forward, data-dense aesthetic inspired by military command centers and Bloomberg terminals.
- **Dark Mode**: The application is strictly dark-themed. All backgrounds, cards, and overlays use dark tones.
- **Glassmorphism**: Panels and sidebars that float over the map must use translucent backgrounds with `backdrop-blur` to create depth without fully obscuring the map beneath.
- **Sharp Edges**: All components, cards, buttons, and widgets must have **zero border-radius** (completely squared, sharp-edged). Rounded corners are forbidden in this design language.
- **Typography**: Use clean, monospaced or semi-monospaced fonts for data-dense displays (event metadata, coordinates). Sans-serif for headings and body text.

### Color System
- **Severity Indicators**: Use a high-contrast color scale to communicate urgency:
  - 🔴 **Red/Crimson** — Critical/Breaking events (active conflicts, disasters)
  - 🟠 **Amber/Orange** — High severity (escalating tensions, economic crises)
  - 🟡 **Yellow** — Moderate (political developments, policy changes)
  - 🔵 **Blue** — Informational (diplomatic meetings, trade agreements)
  - 🟢 **Green** — Positive developments (ceasefires, peace agreements)
- **Category Colors**: In addition to severity, events are color-coded by category (e.g., economic, military, environmental). These must be distinguishable from the severity scale and consistent across the UI.
- **Map Contrast**: All overlay colors must be chosen to remain legible against both the dark Mapbox basemap and the lighter ocean areas.

### Error & Loading UX
- **No Blocking Errors**: Never throw a full-screen error overlay when the real-time connection drops or an API call fails. Instead, use **non-intrusive toast notifications** or a subtle **offline indicator** in the corner.
- **Cached Interaction**: When offline or disconnected, the user must be able to continue interacting with cached map data (panning, zooming, clicking already-loaded events).
- **Loading Skeletons**: Use skeleton/shimmer loading states for sidebars and panels instead of spinners. The map itself should render immediately and populate data progressively.

---

## 3. State Management Architecture

### Zustand as Single Source of Truth
- **Zustand** is the global state manager. All loaded events, active filters, selected event IDs, viewport bounds, and UI state (sidebar open/closed) live in the Zustand store.
- Both the Mapbox map instance and the React UI (sidebars, panels, lists) **react to** and **update** the same Zustand store. This ensures they are always in sync.
- Never let the Mapbox map maintain its own shadow state that the React UI doesn't know about. If an event is selected by clicking a marker on the map, that selection must be written to the Zustand store, not held in a local `useState`.

### Data Flow Pattern
1. **User pans/zooms the map** → viewport bounds update in Zustand.
2. **A React hook or data loader** observes the viewport change → fires a debounced API request with the bounding box.
3. **API returns GeoJSON events** → events are merged into the Zustand store.
4. **Mapbox GeoJSON source** observes the store change → map re-renders the data natively.
5. **Real-time updates** (via WebSocket/SSE) push new events directly into the Zustand store → both map and UI update.

---

## 4. Map Rendering & Performance

### Mapbox Native Layers (Critical)
- All event data must be rendered using **Mapbox GL native layers** fed by GeoJSON sources. This means using `map.addSource()` and `map.addLayer()` — not React DOM nodes.
- **Why**: Rendering 10,000+ events as individual React DOM elements (HTML markers) will destroy performance. Mapbox's WebGL pipeline can handle this volume natively.
- Use Mapbox's built-in **clustering** to group dense markers at high zoom levels. Clusters must display a count and visually indicate the dominant event category within them.

### Visualization Layers
The map must support rendering these distinct layer types:
- **Point Markers**: Color-coded event pins. Use circle or symbol layers with data-driven styling based on event properties (category, severity).
- **Relationship Arcs**: Curved, directional lines connecting source and target locations for events involving multiple countries (e.g., sanctions, trade agreements). Use line layers with curved geometry or consider Deck.gl's ArcLayer if Mapbox native lines are insufficient.
- **Territorial Shading**: Semi-transparent fill layers over country/region polygons to depict ongoing states (e.g., active conflict zones, disputed territories). Use fill layers with data-driven opacity.
- **Cluster Layers**: At higher zoom levels, dense markers must automatically cluster. Clusters should display count badges and use color to reflect the dominant category.

### Dual-Mode Interface
- The application supports two map viewing modes:
  - **2D Regional Map**: Standard flat Mapbox view for zoomed-in, hyper-local exploration.
  - **3D Geopolitical Globe**: A pitched, globe-projection view for macro-level observation of global events and relationship arcs.
- The transition between modes must be seamless (animated camera transition).

---

## 5. Real-Time Updates (Frontend Consumption)

- The frontend must establish a **WebSocket or SSE connection** to the backend to receive newly extracted events in real time.
- When a new event arrives via the stream:
  1. Merge it into the Zustand event store.
  2. The Mapbox GeoJSON source will automatically re-render.
  3. Optionally show a subtle "New events" toast or pulse animation on the relevant map area.
- Implement **automatic reconnection** with exponential backoff if the stream disconnects. Do not throw errors to the user; show a small "Reconnecting..." indicator instead.

---

## 6. Accessibility (a11y)

- **Pragmatic Accessibility**: All UI elements **outside the map** (sidebars, event lists, filter panels, modals, search inputs) must be fully accessible:
  - Proper ARIA labels and roles on all interactive elements.
  - Full keyboard navigation (Tab, Enter, Escape for modals).
  - Focus management when panels open/close.
  - Sufficient color contrast ratios for text overlays.
- **Map Canvas**: The WebGL map canvas is accepted as a visually-dependent element. Do not attempt to make individual map markers keyboard-navigable or screen-reader accessible — that is not feasible with WebGL rendering. Instead, provide an accessible **event list sidebar** as an alternative way to browse the same data.
