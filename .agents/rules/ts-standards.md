---
trigger: glob
description: Strict TypeScript standards, compile-time type safety, concise naming conventions, and React patterns.
globs: '**/*.ts, **/*.tsx'
---

# TypeScript & Frontend Standards

This document establishes the official engineering guidelines, type safety requirements, and code conventions for all TypeScript (`.ts`) and React (`.tsx`) code in Hermes. All AI agents working on frontend applications (`apps/hermes`), end-to-end tests (`apps/hermes-e2e`), or shared libraries (`libs/map`, `libs/shared/ui-components`, `libs/shared/util-types`, `libs/shared/utils`) must strictly adhere to these standards.

---

## 1. Agent Mandate & Core Principles

- **Role**: You are a Senior Full-Stack Spatial & Frontend Engineer.
- **Compile-Time Rigor**: Optimize for absolute type safety at compile time. Eliminate runtime type errors, unsafe type assertions, and implicit fallbacks.
- **The 80/20 Monorepo Boundary**: Keep `apps/hermes` thin (<20%) as a routing, provider, and configuration shell. All reusable components, custom hooks, WebGL/Mapbox integrations, Zustand stores, and utilities must live in shared libraries under `libs/`.
- **Performance First**: Avoid extraneous component re-renders, unnecessary wrapper DOM nodes, and unbounded reactive subscriptions. State must flow unidirectionally.

---

## 2. Strict Type Safety & Prohibitions

- **Strict Prohibition of `any`**: The use of `any` (from TypeScript or any external declaration) is strictly forbidden across all files, functions, parameters, variables, and type definitions.
  - If handling arbitrary or unvalidated external data, use `unknown` combined with explicit type guards (`is`), zod/schema parsing, or narrowing checks.
  - For flexible functions, use generic type parameters with proper constraints (e.g., `<T extends Record<string, unknown>>`).
- **Explicit Return Types**: ALWAYS declare explicit return types on every exported function, custom hook, service method, and utility. Do not rely on implicit compiler inference for public module boundaries.

  ```typescript
  // Bad
  export const fetchEvents = async (bbox: BoundingBox) => { ... };

  // Good
  export const fetchEvents = async (bbox: BoundingBox): Promise<MapEventResponse[]> => { ... };
  ```

- **Prohibition of Loose Type Assertions (`as`)**: Avoid casting with `as TargetType` whenever possible. It bypasses compile-time checks and masks underlying structural mismatches.
  - Use TypeScript's `satisfies` operator when you want to enforce that an object conforms to an interface while preserving its literal type inference.
  - When narrowing values from DOM events or external APIs, use explicit user-defined type guards (`(val: unknown): val is TargetType`).
  - Casting with `as` is only permissible when working with third-party libraries whose ambient type declarations are demonstrably incomplete or inaccurate.

---

## 3. Type Modeling: Types, Interfaces & Enums

- **`interface` for Object Contracts & Props**:
  - Use `interface` for public API schemas, domain models (e.g., [`libs/shared/util-types`](file:///home/pavan/proj/hermes/libs/shared/util-types)), Zustand store state definitions, and React component props.
  - Interfaces provide clean compiler diagnostic errors and support inheritance (`extends`) when composing models.
- **`type` for Unions, Intersections & Primitives**:
  - Use `type` aliases for discriminated unions, mapped types, utility types, tuples, function signatures, and primitive compositions.
- **Strict Prohibition of Native TypeScript `enum`**:
  - Native TypeScript `enum`s generate non-standard runtime JavaScript objects, have well-documented numeric reversibility quirks, and complicate bundle tree-shaking.
  - **Enforce String Literal Unions**: Represent finite status or category sets with string literal unions (e.g., `type IncidentStatus = 'ACTIVE' | 'RESOLVED' | 'ARCHIVED';`).
  - **`as const` Mappings**: When key-value pairs or metadata lookup tables are required, use frozen objects with `as const`:

    ```typescript
    export const EVENT_STATUS = {
      ACTIVE: 'ACTIVE',
      RESOLVED: 'RESOLVED',
      ARCHIVED: 'ARCHIVED',
    } as const;

    export type EventStatus = (typeof EVENT_STATUS)[keyof typeof EVENT_STATUS];
    ```

---

## 4. Elegant & Concise Naming Conventions

- **Minimal & Elegant Identifiers**: Variable, parameter, and property names must be concise and minimal without sacrificing clarity. Prefer industry-standard, elegant abbreviations over bloated, enterprise-style names:
  - `pos` instead of `currentCoordinatesPosition`
  - `bbox` instead of `geographicBoundingBox`
  - `tl` instead of `historicalTimeline`
  - `cfg` instead of `applicationConfiguration`
  - `ctx` instead of `executionContextProvider`
  - `el` instead of `domElementReference`
  - `err` instead of `caughtExceptionError`
  - `fmt` instead of `formattedStringResult`
  - `lngLat` instead of `longitudeAndLatitudeCoordinates`
  - `ref` instead of `reactReferenceContainer`
  - `btn` instead of `clickableActionButton`
- **No Cryptic/Silly Names**: Minimal naming must remain aesthetically pleasing and instantly readable. Never use single-letter mystery variables (outside of standard loop indices like `i` or mathematical coordinates `x, y`), truncated syllables, or confusing acronyms.
- **File Naming**:
  - **React Components**: `PascalCase.tsx` with short, descriptive names (e.g., `EventPopup.tsx`, `LiveClock.tsx`, `TlPanel.tsx`, `BootSequence.tsx`).
  - **Hooks, Stores, Utilities & Types**: `kebab-case.ts` (e.g., `use-map-data-sync.ts`, `api-types.ts`, `store.ts`, `config-context.tsx`).
  - **Route Shells**: `kebab-case.tsx` matching React Router convention (e.g., `map.tsx`, `landing.tsx`, `about.tsx`).
- **Symbol Casing**:
  - **Components, Interfaces, Types**: `PascalCase` (e.g., `MapEventResponse`, `EventPopupProps`).
  - **Functions, Methods, Variables, Hooks**: `camelCase`. Custom hooks must always begin with `use` (e.g., `useMapStore`, `useEventDetails`).
  - **Global Constants & Static Configurations**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_ZOOM`, `MAP_CONFIG`, `REFRESH_INTERVAL_MS`).
  - **Event Handlers & Callbacks**:
    - Internal handler functions must be prefixed with `handle` (e.g., `handleClick`, `handleKeyDown`, `handleZoomIn`).
    - Component callback props must be prefixed with `on` (e.g., `onSelect`, `onComplete`, `onClose`).

---

## 5. Monorepo Boundaries & Import Discipline

- **Strict Type-Only Imports**: ALWAYS use `import type { ... }` when importing TypeScript types, interfaces, or type aliases. This preserves `isolatedModules`, prevents circular dependency runtime issues, and assists bundlers with tree-shaking:

  ```typescript
  // Bad
  import { MapEventResponse, fetchEvents } from '@hermes/util-types';

  // Good
  import { fetchEvents } from '@hermes/util-types';
  import type { MapEventResponse } from '@hermes/util-types';
  ```

- **Workspace Path Aliases**: Strictly use `@hermes/*` tsconfig path aliases (`@hermes/util-types`, `@hermes/ui-components`, `@hermes/map`, `@hermes/utils`) when importing across libraries.
  - Deep relative cross-library paths (e.g., `../../libs/map/src/lib/...`) are strictly forbidden.
  - Relative imports (`./...`, `../...`) are only allowed within the same library or app boundary.
- **Import Grouping**: Group imports cleanly into distinct blocks separated by a single blank line, ordered from outside to inside:
  1. Third-party external packages (`react`, `mapbox-gl`, `zustand`, `@tanstack/react-query`).
  2. Hermes workspace libraries (`@hermes/*`).
  3. Internal relative files (`./...`, `../...`).
  4. Type-only imports (`import type { ... }`).

---

## 6. React, State & Tactical GIS Architecture

- **Explicit Component Props**: Every React component accepting props must define an explicit interface (e.g., `interface TlPanelProps { ... }`). Do not use inline anonymous object types for non-trivial props.
- **The Mapbox Ref Rule**: NEVER store the Mapbox GL `Map` instance in React state (`useState`). Storing it in state triggers recursive re-renders and degrades WebGL rendering performance. ALWAYS hold the map instance in a `useRef<mapboxgl.Map | null>(null)`.
- **Single Source of Truth (No Shadow State)**:
  - Telemetry and map state flow strictly through the Zustand store ([`useMapStore`](file:///home/pavan/proj/hermes/libs/map/src/lib/store/store.ts)).
  - The Mapbox GL instance acts as a pure rendering sink. Never store divergent state inside Mapbox layers or custom marker properties.
- **Data-Driven Styling**: Use Mapbox expressions based on GeoJSON feature properties instead of writing imperative JavaScript loops to adjust marker colors or sizes.
- **Mission Control UI Aesthetic**:
  - **Zero Border Radius**: Never use `rounded-*` classes. The command center aesthetic requires sharp, rectangular corners.
  - **Monospace Typography**: Apply `font-mono` across tactical HUD widgets, telemetry coordinates, and data tables.
  - **Accessible Overlays**: Overlay panels (`TlPanel`, `EventPopup`, HUD controls) must have semantic HTML tags, keyboard navigation (`Escape` key to close), and proper ARIA labels.

---

## 7. Formatting & Code Hygiene

- **Prettier & EditorConfig Alignment**:
  - Indentation: Strictly 2 spaces (no tabs).
  - Quotes: Single quotes (`'`) for JavaScript/TypeScript code; double quotes (`"`) for JSX attributes.
  - Semicolons: Explicit semicolons at the end of every statement.
- **Clean Spacing**: Leave a single blank line between class methods, interfaces, and function declarations. Keep files uncluttered.
- **JSDoc Documentation**: Provide concise JSDoc comments for exported utility functions, custom hook options, and shared data contracts in [`libs/shared/util-types`](file:///home/pavan/proj/hermes/libs/shared/util-types). Avoid redundant comments that simply restate what typed code already clarifies.
