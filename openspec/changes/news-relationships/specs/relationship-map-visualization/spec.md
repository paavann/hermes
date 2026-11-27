# Spec Delta

## Purpose

Visualizes relationships between plotted news events directly on the interactive WebGL map using geodesic arcs, link indicators, active ego-network highlighting, and one-click navigation between connected incidents.

## ADDED Requirements

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

### Requirement: Timeline mode layer isolation
The map SHALL hide all live relationship arc and connected-partner highlight layers while timeline inspection mode is active and restore them when returning to the live map.

#### Scenario: Switching to causal lineage timeline hides live links
- **WHEN** the user opens historical timeline mode from an event popup
- **THEN** live event relationship arcs and partner target rings are hidden until timeline mode closes

### Requirement: Connected-event navigation in event popup
When an event has one or more active relationships, its detail popup SHALL list each connected event with its directional relationship label, category indicator, headline, location, and rationale, and activating an entry SHALL focus the map on that counterpart event and open its popup.

#### Scenario: User navigates from reaction event to primary event
- **WHEN** the user opens the Islamabad event popup and clicks the connected China Tiangong entry
- **THEN** the map camera moves to the China event coordinates and opens the China event detail popup

#### Scenario: Event with no relationships omits connected section
- **WHEN** an event has zero active relationships
- **THEN** the detail popup renders without an empty connected-events section

### Requirement: Link indicators on map pins and cluster inspection
Plotted unclustered pins and cluster inspection entries SHALL indicate when an event participates in one or more relationships so co-located linked events remain discoverable before opening individual popups.

#### Scenario: Cluster list surfaces link counts for co-located events
- **WHEN** the user inspects a cluster containing two co-located events in Pyongyang or South Korea that are linked to one another
- **THEN** each linked item in the cluster list displays its relationship link count alongside its category and importance score
