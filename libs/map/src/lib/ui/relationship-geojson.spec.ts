import { describe, expect, it } from 'vitest';

import type {
  MapEventResponse,
  MapRelationshipEdgeResponse,
} from '@hermes/util-types';

import {
  buildActorGeoJson,
  buildRelationshipGeoJson,
  greatCircleSegments,
} from './relationship-geojson';

function makeEdge(
  overrides: Partial<MapRelationshipEdgeResponse> = {},
): MapRelationshipEdgeResponse {
  return {
    id: 'rel-1',
    source_event_id: 'evt-china',
    target_event_id: 'evt-pakistan',
    source_headline: 'Pakistani astronaut boards China space station',
    source_category: 'SCIENCE',
    source_category_color: '#a855f7',
    source_location_name: 'China',
    source_latitude: 34.79,
    source_longitude: 103.71,
    target_headline: 'SUPARCO watch party celebrates docking',
    target_category: 'TECHNOLOGY',
    target_category_color: '#00f0ff',
    target_location_name: 'Islamabad, Pakistan',
    target_latitude: 33.6946,
    target_longitude: 73.0646,
    relationship_type: 'REACTION',
    confidence: 0.91,
    rationale: 'Crowds gathered in Islamabad to watch the orbital docking.',
    ...overrides,
  };
}

describe('greatCircleSegments', () => {
  it('generates a 24-segment spherical arc with midpoint northward curvature in northern hemisphere', () => {
    const segments = greatCircleSegments([73.0646, 33.6946], [103.71, 34.79]);

    expect(segments).toHaveLength(1);
    expect(segments[0]).toHaveLength(25);
    expect(segments[0][0]).toEqual([73.0646, 33.6946]);
    expect(segments[0][24]).toEqual([103.71, 34.79]);

    // Great circle between equal-ish northern latitudes bows northward above straight lerp
    const midpoint = segments[0][12];
    const flatMidLat = (33.6946 + 34.79) / 2;
    expect(midpoint[1]).toBeGreaterThan(flatMidLat);
  });

  it('splits Pacific arcs across the antimeridian without wrap-around jumps', () => {
    const segments = greatCircleSegments([170, 20], [-170, 22]);

    expect(segments).toHaveLength(2);
    expect(segments[0][segments[0].length - 1][0]).toBe(180);
    expect(segments[1][0][0]).toBe(-180);
    expect(segments[0][segments[0].length - 1][1]).toBeCloseTo(
      segments[1][0][1],
      4,
    );

    for (const part of segments) {
      for (let i = 1; i < part.length; i += 1) {
        expect(Math.abs(part[i][0] - part[i - 1][0])).toBeLessThanOrEqual(180);
      }
    }
  });

  it('handles coincident coordinates without NaN output', () => {
    const segments = greatCircleSegments([125.75, 39.03], [125.75, 39.03]);

    expect(segments).toEqual([
      [
        [125.75, 39.03],
        [125.75, 39.03],
      ],
    ]);
  });
});

describe('buildRelationshipGeoJson', () => {
  it('marks baseline arcs inactive and emits no partners when no event is selected', () => {
    const result = buildRelationshipGeoJson([makeEdge()], null);

    expect(result.edges.features).toHaveLength(1);
    expect(result.edges.features[0].properties.is_active).toBe(false);
    expect(result.partners.features).toHaveLength(0);
  });

  it('highlights the selected event ego-network and deduplicates partner points', () => {
    const chinaToPak = makeEdge();
    const pakToKorea = makeEdge({
      id: 'rel-2',
      source_event_id: 'evt-north-korea',
      target_event_id: 'evt-south-korea',
      source_latitude: 39.03,
      source_longitude: 125.75,
      target_latitude: 37.56,
      target_longitude: 126.97,
      relationship_type: 'CAUSED',
    });

    const result = buildRelationshipGeoJson(
      [chinaToPak, pakToKorea],
      'evt-pakistan',
    );

    expect(result.edges.features[0].properties.is_active).toBe(true);
    expect(result.edges.features[1].properties.is_active).toBe(false);
    expect(result.partners.features).toHaveLength(1);
    expect(result.partners.features[0].properties.id).toBe('evt-china');
    expect(result.partners.features[0].geometry.coordinates).toEqual([
      103.71,
      34.79,
    ]);
  });
});

function makeMapEvent(
  overrides: Partial<MapEventResponse> = {},
): MapEventResponse {
  return {
    id: 'evt-gaza',
    ai_headline: 'Israeli air strikes kill 8 in Gaza Strip',
    category: 'CONFLICT',
    category_color: '#ef4444',
    location_name: 'Gaza Strip',
    latitude: 31.5411,
    longitude: 34.4634,
    importance_score: 45,
    verification_status: 'CORROBORATED',
    selection_tier: 'PRIMARY',
    impact_level: 'MAJOR',
    scope: 'CITY',
    event_time: '2026-11-26T09:00:00Z',
    article_count: 2,
    source_count: 2,
    family_count: 2,
    independent_origin_count: 2,
    relationship_count: 0,
    actors: [
      {
        name: 'Israel',
        kind: 'STATE',
        role: 'ACTOR',
        location_name: 'Israel',
        country_code: 'IL',
        latitude: 31.0461,
        longitude: 34.8516,
      },
      {
        name: 'Local Official',
        kind: 'PERSON',
        role: 'TARGET',
        location_name: 'Gaza Strip',
        country_code: 'PS',
        latitude: 31.5411,
        longitude: 34.4634,
      },
      {
        name: 'Unresolved Org',
        kind: 'ORGANIZATION',
        role: 'PARTICIPANT',
        location_name: null,
        country_code: null,
        latitude: null,
        longitude: null,
      },
    ],
    thread_id: null,
    ...overrides,
  };
}

describe('buildActorGeoJson', () => {
  it('draws subtle cross-border dashed vectors without cluttering anchors when idle', () => {
    const result = buildActorGeoJson([makeMapEvent()], null);

    expect(result.vectors.features).toHaveLength(1);
    expect(result.vectors.features[0].properties).toMatchObject({
      event_id: 'evt-gaza',
      actor_name: 'Israel',
      is_active: false,
    });
    expect(result.anchors.features).toHaveLength(0);
  });

  it('illuminates cross-border vectors and emits non-event anchor badges when active', () => {
    const result = buildActorGeoJson([makeMapEvent()], 'evt-gaza');

    expect(result.vectors.features).toHaveLength(1);
    expect(result.vectors.features[0].properties.is_active).toBe(true);
    expect(result.anchors.features).toHaveLength(1);
    expect(result.anchors.features[0].properties.name).toBe('Israel');
    expect(result.anchors.features[0].geometry.coordinates).toEqual([
      34.8516,
      31.0461,
    ]);
  });
});
