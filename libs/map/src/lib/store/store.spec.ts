import { describe, it, expect, beforeEach } from 'vitest';
import { useMapStore } from './store';

describe('useMapStore', () => {
  beforeEach(() => {
    useMapStore.setState({
      selectedEventId: null,
      selectedEventLngLat: null,
      viewport: null,
      isTlMode: false,
      tlTargetId: null,
    });
  });

  it('initializes with default values', () => {
    const state = useMapStore.getState();
    expect(state.selectedEventId).toBeNull();
    expect(state.selectedEventLngLat).toBeNull();
    expect(state.viewport).toBeNull();
    expect(state.isTlMode).toBe(false);
    expect(state.tlTargetId).toBeNull();
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
});
