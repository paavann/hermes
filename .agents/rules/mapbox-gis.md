---
trigger: always_on
description: Strict rules for Mapbox GL JS and Geospatial logic.
---

# Mapbox & GIS Standards

- **Mapbox Ref Rule**: NEVER store the Mapbox GL `Map` instance in React state (`useState`), as it causes massive performance degradation. Strictly use `useRef` to hold the map instance.
- **Data-Driven Styling**: Strictly use Mapbox's Data-Driven Styling (expressions based on feature properties) instead of writing imperative JavaScript loops to change marker colors.
- **No Magic Numbers**: Extract all hardcoded thresholds, intervals, and Mapbox zoom-level integers into named constants (e.g., `DEFAULT_ZOOM = 5`).
