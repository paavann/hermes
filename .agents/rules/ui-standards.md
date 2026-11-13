---
trigger: glob
description: Minimalistic tactical mission-control UI standards, cyan/bone/amber palette, Space Grotesk display type, GSAP/Tailwind motion, and HUD layout rules.
globs: '**/*.tsx, **/*.css'
---

# UI & Visual Design Standards

## 1. Visual Philosophy & Anti-Clutter Rules

- **Minimalistic Tactical Aesthetic**: Terminal and military-grade analytical precision, kept clean and functional.
- **No Fake Jargon or Decorative Fluff**: Never invent filler sci-fi labels, fake telemetry noise, or meaningless status codes to make the UI look "complex." Every label, readout, and control must represent real application data or actions.
- **Strictly Solid Surfaces**: All panels, overlays, and containers must use opaque, solid background fills (`bg-black`, `bg-obsidian`, `bg-onyx`). Glassmorphism, `backdrop-blur`, translucent panels, drop shadows (`shadow-*`), and neon outer glows (`drop-shadow`, `box-shadow` glow) are strictly prohibited.

## 2. Color Palette & Semantic Encoding

- **Base Canvas & Surfaces**: Pure `#000000` canvas with layered solid neutrals: `obsidian` `#07080A`, `onyx` `#0B0D10`, `graphite` `#12151A`, separated by `1px` hairline structural borders.
- **Primary Accent (`#00F0FF`)**: Electric cyan (`#00F0FF`) is the primary interactive accent for active selections, focus rings, active borders, and primary highlights—used flat without glow effects.
- **Bone & Ivory Secondary**: Warm `ivory` `#F1EDE2` and `bone` `#D7D0BF` carry body copy, headlines, and structural labels instead of pure white.
- **Warm Signal (`#FFB454`)**: Reserve `signal-amber` for a single secondary signal per surface—feed status, trend metrics, or live indicators. Never use it as a second primary accent.
- **Semantic Color Coding**: Use strict, flat semantic tokens from `apps/hermes/styles.css` for geospatial event impact, velocity, status, and citation badges. Never hardcode arbitrary hex colors inside components.

## 3. Geometry, Borders & Elevation

- **Zero Border Radius**: Strictly `0px` sharp rectangular corners everywhere (`rounded-none`, `--radius-*: initial`). No rounded buttons, inputs, cards, or modals.
- **Structural Borders & L-Shaped Brackets**: Separate overlapping panels from the map using solid background fills and `1px` hairline borders. Use L-shaped corner brackets/reticles on key HUD containers and active frames.

## 4. Typography & Data Formatting

- **Display Face for Headlines**: Use `Space Grotesk` (`font-display`) for hero headlines, section titles, card titles, popups, and the brand wordmark. Tighten tracking (`tracking-[-0.03em]`) and leading (`leading-[0.98]`) on large display type.
- **Monospace for UI & Data**: Enforce `JetBrains Mono` (`font-mono`) for all UI chrome, HUD readouts, labels, buttons, forms, metadata, and long-form chat/timeline prose.
- **Headers & Labels**: Style all section headers, panel titles, and category badges in `UPPERCASE` with `tracking-wider` and `text-xs`.
- **Numeric Alignment**: Apply `tabular-nums` to all coordinates, timestamps, counters, and confidence/decay metrics.

## 5. Motion & Micro-Interactions (Tailwind + GSAP)

- **Snappy Mechanical Feel**: Transitions must feel instant, crisp, and mechanical (100–150ms linear/ease-out snaps, zero bounce).
- **Tooling Split**: Use Tailwind CSS transitions (`transition-colors`, `transition-transform`) for simple state/hover swaps, and **GSAP** for sequenced or complex component animations (boot reveals, staggered HUD mounts, text roll/scramble micro-interactions across interactive components).

## 6. Map HUD Layout & Panel Behavior

- **Full-Bleed Map Viewport**: On `/map`, the Mapbox canvas always occupies `100dvh` full-bleed; panels render as solid floating HUD overlays.
- **Persistent Command Chrome**: Keep a compact solid `h-12` top command bar (identity, center coordinates, event/cited counts, feed status, UTC clock) and an `h-7` bottom status strip (SRID, projection, live category legend, viewport center). Every readout must derive from live map or feed state.
- **Mutually Exclusive Panels**: Only one major drawer/panel (`ChatPanel` or `TlPanel`) may be open at a time—opening one automatically closes the other.
- **Compact Panel Chrome**: Every open panel/overlay must include a compact `1px`-bordered header bar containing an `UPPERCASE` title and an explicit close trigger.

## 7. Controls, Icons & Feedback States

- **Centralized Primitives**: All base UI elements live in `libs/shared/ui-components/src/components/ui/` (`base-sera` shadcn style, `@base-ui/react`). Never create local base primitives in `apps/*` or feature `libs/*`.
- **Tailwind v4 Discipline**: Style via Tailwind utilities merged with `cn()`. Standalone `.css` / `.module.css` files and inline `style={{ ... }}` are banned (except dynamic runtime WebGL/canvas transforms).
- **Hard Color Inversion on Hover/Active**: Interactive buttons (`TacticalActionBtn`, `RollButton`, `Button`) use hard color inversion (e.g., dark background + crisp border inverting to solid high-contrast fill + dark text).
- **Phosphor Icons**: Use `@phosphor-icons/react` with **`bold`** weight by default, sized at `14px` inline (scaling contextually for standalone triggers).
- **Terminal Loading States**: Use terminal-style blinking text/cursors (e.g., `SYNTHESIZING TIMELINE...`) for streaming, retrieval, and async operations instead of decorative spinners.
- **Focus & Keyboard UX**: Enforce sharp `1px` high-contrast focus outlines (`focus-visible:outline-1`) and standard HUD keyboard shortcuts (`Esc` to close active panels, `/` to focus chat input).
- **Desktop-First**: Design primarily for desktop viewports, collapsing HUD overlays cleanly into full-width stacked drawers on narrow screens (`<768px`).