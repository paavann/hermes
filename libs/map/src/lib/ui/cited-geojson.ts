import type { Feature, FeatureCollection, Point } from 'geojson';

import type { CitedEvent } from '../store/store';

export interface CitedEventProperties {
  id: string;
  category_color: string | null;
}

export type CitedEventFeature = Feature<Point, CitedEventProperties>;

/** Build the unclustered GeoJSON source behind the citation highlight rings. */
export function createCitedGeoJson(
  events: readonly CitedEvent[],
): FeatureCollection<Point, CitedEventProperties> {
  const features: CitedEventFeature[] = events.map((event) => ({
    type: 'Feature',
    geometry: {
      type: 'Point',
      coordinates: [event.longitude, event.latitude],
    },
    properties: {
      id: event.id,
      category_color: event.category_color ?? null,
    },
  }));

  return { type: 'FeatureCollection', features };
}
