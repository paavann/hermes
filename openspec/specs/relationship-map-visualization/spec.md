# Relationship Map Visualization Specification

## Purpose

Visualizes relationships between plotted news events directly on the interactive WebGL map using geodesic arcs, link indicators, active ego-network highlighting, and one-click navigation between connected incidents.

## Requirements

### Requirement: Default-on viewport relationship arcs with HUD toggle
The live map SHALL render viewport relationship edges by default as curved geodesic arcs connecting linked event coordinates (segmented cleanly across the antimeridian without wrap-around streaks), and SHALL provide a HUD toggle to show or hide viewport relationship arcs.

#### Scenario: Geodesic arcs visible on initial map load
- **WHEN** the live map loads a viewport containing connected events such as Beijing and Islamabad
- **THEN** curved geodesic arcs are drawn between the connected events' coordinates without requiring prior pin selection

#### Scenario: User toggles relationship arcs off and on
- **WHEN** the user activates the `[LINKS]` toggle in the map HUD while arcs are visible
- **THEN** background viewport relationship arcs hide cleanly, and activating the toggle again restores them

### Requirement: Selected-pin ego-network highlighting
When an event is selected, the map SHALL prominently highlight all relationship arcs touching the selected event and highlight its connected partner pins (including off-screen or clustered counterparts), while dimming unrelated background arcs.

#### Scenario: Selecting an event illuminates its connections
- **WHEN** the user selects the Islamabad watch-party pin while China lies off-screen or across the map
- **THEN** the arc connecting Islamabad and China brightens, a target ring highlights the China counterpart coordinate, and unrelated background arcs dim

#### Scenario: Deselecting restores baseline arc styling
- **WHEN** the user closes the selected event popup
- **THEN** partner target rings clear and visible arcs return to default viewport opacity

### Requirement: High-contrast color-coded relationship arcs with persistent selection styling and glow
The live map SHALL render `Event <-> Event` arcs using persistent neon type colors (`CAUSED` amber, `FOLLOW_UP` cyan, `REACTION` magenta, `RELATED` violet) preserved across both inactive and selected states, backed by an outer halo glow layer and higher contrast baseline/active opacity instead of collapsing selected links to a single color.

#### Scenario: Relationship arcs preserve distinct type colors when selected
- **WHEN** the user selects an event that has both an incoming `REACTION` arc and an outgoing `CAUSED` arc
- **THEN** the `REACTION` arc stays vivid magenta (`#ff4fd8`) and the `CAUSED` arc stays bright amber (`#ffb454`) with increased width and halo glow instead of collapsing both edges to uniform cyan

#### Scenario: Baseline arcs remain clearly readable at global zoom
- **WHEN** the live map displays viewport relationship edges over satellite terrain and bright map borders with `[LINKS]` enabled
- **THEN** each arc renders with higher baseline opacity (`~0.70`) and an underlying glow casing so all four relationship types remain immediately distinguishable

### Requirement: Distinct cross-border dashed actor-origin vectors (`WHO` <-> `WHERE`)
When a plotted event retains a `WHO` actor geocoded in a distinct country or location from the `WHERE` pin, the map SHALL render a dashed geodesic vector from the actor's coordinates to the event pin, displayed subtly when `[LINKS]` is ON and highlighted with non-event diamond/ring Actor Anchor badges on selection or hover.

#### Scenario: Cross-border attack connects actor origin to incident pin without faking a second event
- **WHEN** an event such as `"Israeli attacks on Gaza kill eight people"` is plotted at `Gaza Strip` with cross-border actor `"Israel"` and `[LINKS]` is enabled
- **THEN** a dashed actor vector links `Israel`'s coordinates to the `Gaza Strip` event pin in a distinct style from solid `Event <-> Event` arcs, and hovering or selecting the `Gaza Strip` pin illuminates the dashed vector and shows a non-event Actor Anchor badge at `Israel`

#### Scenario: Deselecting hides temporary actor anchor badges while preserving subtle preview
- **WHEN** the user closes the selected event popup while `[LINKS]` remains ON
- **THEN** the highlighted Actor Anchor badge clears and cross-border actor vectors return to subtle dashed preview state (or hide entirely when `[LINKS]` is toggled OFF)

### Requirement: Timeline mode layer isolation
The map SHALL hide all live relationship arc, halo glow, partner highlight, actor vector, and actor anchor layers while timeline inspection mode is active and restore them when returning to the live map.

#### Scenario: Switching to causal lineage timeline hides live links and actor vectors
- **WHEN** the user opens historical timeline mode from an event popup
- **THEN** live event relationship arcs, glow halos, partner target rings, actor vectors, and actor anchor badges are hidden until timeline mode closes

### Requirement: Inline link-type legend, retained actors, and color-coded popup badges
When `[LINKS]` is active in `MapHud`, the HUD SHALL display a compact inline color legend identifying `CAUSED`, `FOLLOW_UP`, `REACTION`, `RELATED`, and dashed cross-border `ACTOR` links; inside `EventPopup`, retained `WHO` actors SHALL appear with role/country badges alongside `WHERE` location, and each `CONNECTED EVENTS` entry SHALL render its relationship badge using the matching type color.

#### Scenario: HUD displays link type legend when `[LINKS]` is toggled ON
- **WHEN** `[LINKS]` is active in the map HUD
- **THEN** a compact color legend shows the swatches for `CAUSED`, `FOLLOW_UP`, `REACTION`, `RELATED`, and dashed `ACTOR`, and hides cleanly when `[LINKS]` is toggled OFF

#### Scenario: User navigates from reaction event to primary event via color-coded popup entry
- **WHEN** the user opens the Islamabad event popup and clicks the color-coded connected China Tiangong entry
- **THEN** the map camera moves to the China event coordinates and opens the China event detail popup

#### Scenario: Event with retained actors displays WHO alongside WHERE in popup
- **WHEN** the user opens an event popup that retains external or institutional actors (such as `"Israel"` for a Gaza event or `"China"` / `"SUPARCO"` for a Pakistan event)
- **THEN** the popup displays an `ACTORS` section with each actor's name and role/country while preserving the `WHERE` incident header, and omits `CONNECTED EVENTS` if zero `Event <-> Event` edges exist

### Requirement: Link indicators on map pins and cluster inspection
Plotted unclustered pins and cluster inspection entries SHALL indicate when an event participates in one or more relationships so co-located linked events remain discoverable before opening individual popups.

#### Scenario: Cluster list surfaces link counts for co-located events
- **WHEN** the user inspects a cluster containing two co-located events in Pyongyang or South Korea that are linked to one another
- **THEN** each linked item in the cluster list displays its relationship link count alongside its category and importance score
