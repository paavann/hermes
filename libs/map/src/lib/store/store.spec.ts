import { describe, it, expect, beforeEach } from 'vitest';
import { useMapStore } from './store';
import type { CitedEvent } from './store';

const firstEvent: CitedEvent = {
  id: 'event-1',
  latitude: 46.2,
  longitude: 6.1,
  category_color: '#00f0ff',
};

const secondEvent: CitedEvent = {
  id: 'event-2',
  latitude: -33.9,
  longitude: 151.2,
  category_color: null,
};

describe('useMapStore', () => {
  beforeEach(() => {
    useMapStore.setState({
      selectedEventId: null,
      selectedEventLngLat: null,
      viewport: null,
      isTlMode: false,
      tlTargetId: null,
      citedEvents: [],
      focusRequest: null,
    });
  });

  it('initializes with default values', () => {
    const state = useMapStore.getState();
    expect(state.selectedEventId).toBeNull();
    expect(state.selectedEventLngLat).toBeNull();
    expect(state.viewport).toBeNull();
    expect(state.isTlMode).toBe(false);
    expect(state.tlTargetId).toBeNull();
    expect(state.citedEvents).toEqual([]);
    expect(state.focusRequest).toBeNull();
  });

  it('updates selected event ID and coordinates', () => {
    useMapStore.getState().setSelectedEventId('event-123', [12.34, 56.78]);
    const state = useMapStore.getState();
    expect(state.selectedEventId).toBe('event-123');
    expect(state.selectedEventLngLat).toEqual([12.34, 56.78]);
  });

  it('updates viewport bounding box', () => {
    const bbox = { north: 50, south: 40, east: 10, west: 0 };
    useMapStore.getState().setViewport(bbox);
    expect(useMapStore.getState().viewport).toEqual(bbox);
  });

  it('updates timeline mode and target ID', () => {
    useMapStore.getState().setTlMode(true, 'event-456');
    const state = useMapStore.getState();
    expect(state.isTlMode).toBe(true);
    expect(state.tlTargetId).toBe('event-456');
  });

  it('replaces and clears cited events', () => {
    useMapStore.getState().setCitedEvents([firstEvent, secondEvent]);
    expect(useMapStore.getState().citedEvents).toEqual([
      firstEvent,
      secondEvent,
    ]);

    useMapStore.getState().setCitedEvents([secondEvent]);
    expect(useMapStore.getState().citedEvents).toEqual([secondEvent]);

    useMapStore.getState().setCitedEvents([]);
    expect(useMapStore.getState().citedEvents).toEqual([]);
  });

  it('focuses an event and increments the nonce on every request', () => {
    useMapStore.getState().focusEvent('event-1', [6.1, 46.2]);
    const first = useMapStore.getState();

    expect(first.focusRequest).toEqual({
      eventId: 'event-1',
      lngLat: [6.1, 46.2],
      nonce: expect.any(Number),
    });
    expect(first.selectedEventId).toBe('event-1');
    expect(first.selectedEventLngLat).toEqual([6.1, 46.2]);

    useMapStore.getState().focusEvent('event-1', [6.1, 46.2]);
    const second = useMapStore.getState();

    expect(second.focusRequest?.nonce).toBeGreaterThan(
      first.focusRequest?.nonce ?? 0,
    );
  });
});
