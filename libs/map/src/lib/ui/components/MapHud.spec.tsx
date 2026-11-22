import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { MapEventResponse } from '@hermes/util-types';

import { useMapStore } from '../../store/store';
import { MapHud } from './MapHud';

function makeEvent(
  id: string,
  category: string,
  color: string,
): MapEventResponse {
  return {
    id,
    ai_headline: `Headline ${id}`,
    category,
    category_color: color,
    location_name: null,
    latitude: 0,
    longitude: 0,
    importance_score: 50,
    verification_status: 'CORROBORATED',
    selection_tier: 'FILLER',
    impact_level: 'MODERATE',
    scope: 'LOCAL',
    event_time: null,
    article_count: 1,
    source_count: 1,
    family_count: 1,
    independent_origin_count: 1,
    thread_id: null,
  };
}

describe('MapHud', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-16T12:34:56Z'));
    useMapStore.setState({
      viewport: null,
      citedEvents: [],
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders identity, UTC clock, and zeroed telemetry before data arrives', () => {
    render(<MapHud events={[]} isFetching={false} />);

    expect(screen.getByText('HERMES')).toBeTruthy();
    expect(screen.getByText('LIVE MAP')).toBeTruthy();
    expect(screen.getByText('12:34:56 UTC')).toBeTruthy();
    expect(screen.getByText('000')).toBeTruthy();
    expect(screen.getAllByText('——')).toHaveLength(2);
    expect(screen.getByText('AWAITING FEED')).toBeTruthy();
  });

  it('derives center coordinates, wraps longitude, and pads the event count', () => {
    useMapStore.setState({
      viewport: { north: 50, south: 30, east: 200, west: 170 },
    });
    const events = [makeEvent('a', 'ENVIRONMENT', '#22c55e')];

    render(<MapHud events={events} isFetching={false} />);

    expect(screen.getByText('40.00°N')).toBeTruthy();
    expect(screen.getByText('175.00°W')).toBeTruthy();
    expect(screen.getByText('001')).toBeTruthy();
  });

  it('formats southern and western hemispheres with negative values', () => {
    useMapStore.setState({
      viewport: { north: -10, south: -30, east: -160, west: -170 },
    });

    render(<MapHud events={[]} isFetching={false} />);

    expect(screen.getByText('20.00°S')).toBeTruthy();
    expect(screen.getByText('165.00°W')).toBeTruthy();
  });

  it('deduplicates categories and shows at most four legend entries', () => {
    const events = [
      makeEvent('a', 'ENVIRONMENT', '#22c55e'),
      makeEvent('b', 'ENVIRONMENT', '#22c55e'),
      makeEvent('c', 'CONFLICT', '#ffb454'),
      makeEvent('d', 'HEALTH', '#f472b6'),
      makeEvent('e', 'ECONOMY', '#38bdf8'),
      makeEvent('f', 'TECH', '#a78bfa'),
    ];

    render(<MapHud events={events} isFetching={false} />);

    expect(screen.getByText('006')).toBeTruthy();
    expect(screen.getByTitle('ENVIRONMENT')).toBeTruthy();
    expect(screen.getByTitle('CONFLICT')).toBeTruthy();
    expect(screen.getByTitle('HEALTH')).toBeTruthy();
    expect(screen.getByTitle('ECONOMY')).toBeTruthy();
    expect(screen.queryByTitle('TECH')).toBeNull();
    expect(screen.queryByText('AWAITING FEED')).toBeNull();
  });

  it('clears its clock interval on unmount', () => {
    const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');
    const { unmount } = render(<MapHud events={[]} isFetching={false} />);

    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
  });
});
