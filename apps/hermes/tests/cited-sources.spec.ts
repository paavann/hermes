import { describe, expect, it } from 'vitest';

import type { ChatSource } from '@hermes/util-types';

import { citedEventsFromSources } from '../app/components/map/cited-sources';

function source(overrides: Partial<ChatSource>): ChatSource {
  return {
    kind: 'event',
    id: 'source-1',
    event_id: 'event-1',
    title: 'Source',
    url: null,
    source_name: null,
    published_at: null,
    retrieved_at: null,
    latitude: 46.2,
    longitude: 6.1,
    is_external: false,
    snippet: null,
    ...overrides,
  };
}

describe('citedEventsFromSources', () => {
  it('maps plotted sources and deduplicates by event', () => {
    const cited = citedEventsFromSources([
      source({ id: 'event-source', event_id: 'event-1' }),
      source({
        id: 'article-source',
        kind: 'article',
        event_id: 'event-1',
        latitude: 10,
        longitude: 20,
      }),
      source({
        id: 'timeline-source',
        kind: 'timeline',
        event_id: 'event-2',
        latitude: -33.8,
        longitude: 151.2,
      }),
    ]);

    expect(cited).toEqual([
      { id: 'event-1', latitude: 46.2, longitude: 6.1 },
      { id: 'event-2', latitude: -33.8, longitude: 151.2 },
    ]);
  });

  it('skips web sources and sources without plotted coordinates', () => {
    const cited = citedEventsFromSources([
      source({
        id: 'web-source',
        kind: 'web',
        event_id: null,
        latitude: null,
        longitude: null,
      }),
      source({ id: 'unplotted', latitude: null }),
      source({ id: 'unplotted-2', longitude: null }),
    ]);

    expect(cited).toEqual([]);
  });

  it('returns an empty list when the conversation clears its sources', () => {
    expect(citedEventsFromSources([])).toEqual([]);
  });
});
