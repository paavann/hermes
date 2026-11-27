import type { Feature, FeatureCollection, LineString, Point } from 'geojson';

import type {
  EventActorItem,
  EventActorKind,
  EventActorRole,
  EventRelationshipType,
  MapEventResponse,
  MapRelationshipEdgeResponse,
} from '@hermes/util-types';

const DEG_TO_RAD = Math.PI / 180;
const RAD_TO_DEG = 180 / Math.PI;
const DEFAULT_ARC_SEGMENTS = 24;

export type LngLat = [number, number];

export interface RelationshipEdgeProperties {
  id: string;
  source_event_id: string;
  target_event_id: string;
  relationship_type: EventRelationshipType;
  confidence: number;
  rationale: string;
  is_active: boolean;
}

export interface RelationshipPartnerProperties {
  id: string;
  headline: string;
  category: string;
  category_color: string;
  location_name: string | null;
  relationship_type: EventRelationshipType;
  rationale: string;
}

export interface RelationshipGeoJson {
  edges: FeatureCollection<LineString, RelationshipEdgeProperties>;
  partners: FeatureCollection<Point, RelationshipPartnerProperties>;
}

export interface ActorVectorProperties {
  event_id: string;
  actor_name: string;
  actor_kind: EventActorKind;
  actor_role: EventActorRole;
  location_name: string | null;
  country_code: string | null;
  is_active: boolean;
}

export interface ActorAnchorProperties {
  event_id: string;
  name: string;
  kind: EventActorKind;
  role: EventActorRole;
  location_name: string | null;
  country_code: string | null;
}

export interface ActorOverlayGeoJson {
  vectors: FeatureCollection<LineString, ActorVectorProperties>;
  anchors: FeatureCollection<Point, ActorAnchorProperties>;
}

const MIN_ACTOR_VECTOR_DEGREES = 0.05;

function hasExternalActorCoords(
  actor: EventActorItem,
  event: MapEventResponse,
): actor is EventActorItem & { latitude: number; longitude: number } {
  if (
    typeof actor.latitude !== 'number' ||
    typeof actor.longitude !== 'number' ||
    !Number.isFinite(actor.latitude) ||
    !Number.isFinite(actor.longitude)
  ) {
    return false;
  }
  return (
    Math.hypot(
      actor.longitude - event.longitude,
      actor.latitude - event.latitude,
    ) > MIN_ACTOR_VECTOR_DEGREES
  );
}

/** Build dashed geodesic WHO -> WHERE vectors and active non-event actor anchors. */
export function buildActorGeoJson(
  events: readonly MapEventResponse[],
  activeEventId: string | null,
  segments: number = DEFAULT_ARC_SEGMENTS,
): ActorOverlayGeoJson {
  const vectorFeatures: Feature<LineString, ActorVectorProperties>[] = [];
  const anchorMap = new Map<string, Feature<Point, ActorAnchorProperties>>();

  for (const event of events) {
    if (!Array.isArray(event.actors) || event.actors.length === 0) {
      continue;
    }
    const isActive = activeEventId !== null && event.id === activeEventId;

    for (const actor of event.actors) {
      if (!hasExternalActorCoords(actor, event)) {
        continue;
      }

      const properties: ActorVectorProperties = {
        event_id: event.id,
        actor_name: actor.name,
        actor_kind: actor.kind,
        actor_role: actor.role,
        location_name: actor.location_name,
        country_code: actor.country_code,
        is_active: isActive,
      };

      const parts = greatCircleSegments(
        [actor.longitude, actor.latitude],
        [event.longitude, event.latitude],
        segments,
      );
      for (const coordinates of parts) {
        vectorFeatures.push({
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates,
          },
          properties,
        });
      }

      if (!isActive) {
        continue;
      }

      const dedupeKey = `${actor.name.trim().toLowerCase()}|${actor.longitude.toFixed(3)}|${actor.latitude.toFixed(3)}`;
      if (!anchorMap.has(dedupeKey)) {
        anchorMap.set(dedupeKey, {
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [actor.longitude, actor.latitude],
          },
          properties: {
            event_id: event.id,
            name: actor.name,
            kind: actor.kind,
            role: actor.role,
            location_name: actor.location_name,
            country_code: actor.country_code,
          },
        });
      }
    }
  }

  return {
    vectors: {
      type: 'FeatureCollection',
      features: vectorFeatures,
    },
    anchors: {
      type: 'FeatureCollection',
      features: Array.from(anchorMap.values()),
    },
  };
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function toCartesian(lng: number, lat: number): [number, number, number] {
  const phi = lat * DEG_TO_RAD;
  const lambda = lng * DEG_TO_RAD;
  const cosPhi = Math.cos(phi);
  return [
    cosPhi * Math.cos(lambda),
    cosPhi * Math.sin(lambda),
    Math.sin(phi),
  ];
}

function toLngLat(vec: readonly [number, number, number]): LngLat {
  const [x, y, z] = vec;
  const lng = Math.atan2(y, x) * RAD_TO_DEG;
  const lat = Math.asin(clamp(z, -1, 1)) * RAD_TO_DEG;
  return [lng, lat];
}

function orthogonalAxis(
  vec: readonly [number, number, number],
): [number, number, number] {
  const ref: readonly [number, number, number] =
    Math.abs(vec[0]) < 0.9 ? [1, 0, 0] : [0, 1, 0];
  const cx = vec[1] * ref[2] - vec[2] * ref[1];
  const cy = vec[2] * ref[0] - vec[0] * ref[2];
  const cz = vec[0] * ref[1] - vec[1] * ref[0];
  const norm = Math.hypot(cx, cy, cz) || 1;
  return [cx / norm, cy / norm, cz / norm];
}

function interpolateGreatCircle(
  start: LngLat,
  end: LngLat,
  segments: number = DEFAULT_ARC_SEGMENTS,
): LngLat[] {
  const a = toCartesian(start[0], start[1]);
  const b = toCartesian(end[0], end[1]);
  const dot = clamp(a[0] * b[0] + a[1] * b[1] + a[2] * b[2], -1, 1);
  const omega = Math.acos(dot);

  if (omega < 1e-6) {
    return [start, end];
  }

  const sinOmega = Math.sin(omega);
  const antipodal = sinOmega < 1e-6;
  const ortho = antipodal ? orthogonalAxis(a) : null;
  const points: LngLat[] = [];

  for (let i = 0; i <= segments; i += 1) {
    if (i === 0) {
      points.push(start);
      continue;
    }
    if (i === segments) {
      points.push(end);
      continue;
    }

    const t = i / segments;
    if (antipodal && ortho) {
      const angle = Math.PI * t;
      const cosA = Math.cos(angle);
      const sinA = Math.sin(angle);
      points.push(
        toLngLat([
          cosA * a[0] + sinA * ortho[0],
          cosA * a[1] + sinA * ortho[1],
          cosA * a[2] + sinA * ortho[2],
        ]),
      );
      continue;
    }

    const weightA = Math.sin((1 - t) * omega) / sinOmega;
    const weightB = Math.sin(t * omega) / sinOmega;
    points.push(
      toLngLat([
        weightA * a[0] + weightB * b[0],
        weightA * a[1] + weightB * b[1],
        weightA * a[2] + weightB * b[2],
      ]),
    );
  }

  return points;
}

export function splitAntimeridian(points: readonly LngLat[]): LngLat[][] {
  if (points.length === 0) {
    return [];
  }

  const parts: LngLat[][] = [];
  let current: LngLat[] = [points[0]];

  for (let i = 1; i < points.length; i += 1) {
    const prev = current[current.length - 1];
    const next = points[i];
    const diff = next[0] - prev[0];

    if (Math.abs(diff) <= 180) {
      current.push(next);
      continue;
    }

    const exitLng = diff > 180 ? -180 : 180;
    const enterLng = diff > 180 ? 180 : -180;
    const wrappedDelta = diff > 180 ? diff - 360 : diff + 360;
    const fraction = wrappedDelta !== 0 ? (exitLng - prev[0]) / wrappedDelta : 0.5;
    const crossLat = prev[1] + (next[1] - prev[1]) * clamp(fraction, 0, 1);

    current.push([exitLng, crossLat]);
    parts.push(current);
    current = [[enterLng, crossLat], next];
  }

  parts.push(current);
  return parts;
}

export function greatCircleSegments(
  start: LngLat,
  end: LngLat,
  segments: number = DEFAULT_ARC_SEGMENTS,
): LngLat[][] {
  return splitAntimeridian(interpolateGreatCircle(start, end, segments));
}

export function buildRelationshipGeoJson(
  edges: readonly MapRelationshipEdgeResponse[],
  selectedEventId: string | null,
  segments: number = DEFAULT_ARC_SEGMENTS,
): RelationshipGeoJson {
  const edgeFeatures: Feature<LineString, RelationshipEdgeProperties>[] = [];
  const partnerMap = new Map<
    string,
    Feature<Point, RelationshipPartnerProperties>
  >();

  for (const edge of edges) {
    const isActive =
      selectedEventId !== null &&
      (edge.source_event_id === selectedEventId ||
        edge.target_event_id === selectedEventId);

    const properties: RelationshipEdgeProperties = {
      id: edge.id,
      source_event_id: edge.source_event_id,
      target_event_id: edge.target_event_id,
      relationship_type: edge.relationship_type,
      confidence: edge.confidence,
      rationale: edge.rationale,
      is_active: isActive,
    };

    const arcParts = greatCircleSegments(
      [edge.source_longitude, edge.source_latitude],
      [edge.target_longitude, edge.target_latitude],
      segments,
    );

    for (const coordinates of arcParts) {
      edgeFeatures.push({
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates,
        },
        properties,
      });
    }

    if (!isActive || selectedEventId === null) {
      continue;
    }

    const isSourceSelected = edge.source_event_id === selectedEventId;
    const partnerId = isSourceSelected
      ? edge.target_event_id
      : edge.source_event_id;

    if (!partnerMap.has(partnerId)) {
      partnerMap.set(partnerId, {
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: isSourceSelected
            ? [edge.target_longitude, edge.target_latitude]
            : [edge.source_longitude, edge.source_latitude],
        },
        properties: {
          id: partnerId,
          headline: isSourceSelected ? edge.target_headline : edge.source_headline,
          category: isSourceSelected ? edge.target_category : edge.source_category,
          category_color: isSourceSelected
            ? edge.target_category_color
            : edge.source_category_color,
          location_name: isSourceSelected
            ? edge.target_location_name
            : edge.source_location_name,
          relationship_type: edge.relationship_type,
          rationale: edge.rationale,
        },
      });
    }
  }

  return {
    edges: {
      type: 'FeatureCollection',
      features: edgeFeatures,
    },
    partners: {
      type: 'FeatureCollection',
      features: Array.from(partnerMap.values()),
    },
  };
}
