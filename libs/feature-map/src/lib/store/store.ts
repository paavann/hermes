import { create } from 'zustand';

export interface BoundingBox {
  north: number;
  south: number;
  east: number;
  west: number;
}

interface MapState {
  selectedEventId: string | null;
  selectedEventLngLat: [number, number] | null;
  viewport: BoundingBox | null;
  isTlMode: boolean;
  tlTargetId: string | null;

  setSelectedEventId: (id: string | null, lngLat?: [number, number] | null) => void;
  setViewport: (viewport: BoundingBox) => void;
  setTlMode: (active: boolean, targetId?: string | null) => void;
}

export const useMapStore = create<MapState>((set) => ({
  selectedEventId: null,
  selectedEventLngLat: null,
  viewport: null,
  isTlMode: false,
  tlTargetId: null,
  setSelectedEventId: (id, lngLat = null) => set({ selectedEventId: id, selectedEventLngLat: lngLat }),
  setViewport: (viewport) => set({ viewport }),
  setTlMode: (active, targetId = null) => set({ isTlMode: active, tlTargetId: targetId }),
}));
if (typeof window !== 'undefined') (window as any).useMapStore = useMapStore;
