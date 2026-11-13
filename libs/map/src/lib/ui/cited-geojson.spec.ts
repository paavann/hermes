import { describe, expect, it } from 'vitest';

import { createCitedGeoJson } from './cited-geojson';
import type { CitedEvent } from '../store/store';

const firstEvent: CitedEvent = {
  id: 'event-1',
  latitude: 46.2044,
  longitude: 6.1432,
  category_color: '#00f0ff',
};

const secondEvent: CitedEvent = {
  id: 'event-2',
  latitude: -33.8688,
  longitude: 151.2093,
};

describe('createCitedGeoJson', () => {
  it('returns an empty feature collection for no cited events', () => {
    expect(createCitedGeoJson([])).toEqual({
      type: 'FeatureCollection',
      features: [],
    });
  });

  it('maps each cited event to a lon/lat point feature', () => {
    const collection = createCitedGeoJson([firstEvent, secondEvent]);

    expect(collection.features).toHaveLength(2);
    expect(collection.features[0]).toEqual({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [6.1432, 46.2044],
      },
      properties: {
        id: 'event-1',
        category_color: '#00f0ff',
      },
    });
    expect(collection.features[1]).toEqual({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [151.2093, -33.8688],
      },
      properties: {
        id: 'event-2',
        category_color: null,
      },
    });
  });

  it('preserves the order of the cited events', () => {
    const collection = createCitedGeoJson([secondEvent, firstEvent]);

    expect(collection.features.map((feature) => feature.properties.id)).toEqual(
      ['event-2', 'event-1'],
    );
  });
});
