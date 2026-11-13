import { create } from 'zustand';

export interface BoundingBox {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface CitedEvent {
  id: string;
  latitude: number;
  longitude: number;
  category_color?: string | null;
}

export interface FocusRequest {
  eventId: string;
  lngLat: [number, number];
  nonce: number;
}

interface MapState {
  selectedEventId: string | null;
  selectedEventLngLat: [number, number] | null;
  viewport: BoundingBox | null;
  isTlMode: boolean;
  tlTargetId: string | null;
  citedEvents: CitedEvent[];
  focusRequest: FocusRequest | null;

  setSelectedEventId: (
    id: string | null,
    lngLat?: [number, number] | null,
  ) => void;
  setViewport: (viewport: BoundingBox) => void;
  setTlMode: (active: boolean, targetId?: string | null) => void;
  setCitedEvents: (events: CitedEvent[]) => void;
  focusEvent: (eventId: string, lngLat: [number, number]) => void;
}

let focusNonce = 0;

export const useMapStore = create<MapState>((set) => ({
  selectedEventId: null,
  selectedEventLngLat: null,
  viewport: null,
  isTlMode: false,
  tlTargetId: null,
  citedEvents: [],
  focusRequest: null,
  setSelectedEventId: (id, lngLat = null) =>
    set({ selectedEventId: id, selectedEventLngLat: lngLat }),
  setViewport: (viewport) => set({ viewport }),
  setTlMode: (active, targetId = null) =>
    set({ isTlMode: active, tlTargetId: targetId }),
  setCitedEvents: (citedEvents) => set({ citedEvents }),
  focusEvent: (eventId, lngLat) => {
    focusNonce += 1;
    set({
      focusRequest: { eventId, lngLat, nonce: focusNonce },
      selectedEventId: eventId,
      selectedEventLngLat: lngLat,
    });
  },
}));
