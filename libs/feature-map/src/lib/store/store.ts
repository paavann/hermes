import { create } from 'zustand'

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

    setSelectedEventId: (id: string | null, lngLat?: [number, number]) => void;
    setViewport: (viewport: BoundingBox) => void;
}

export const useMapStore = create<MapState>((set) => ({
    selectedEventId: null,
    selectedEventLngLat: null,
    viewport: null,
    setSelectedEventId: (id, lngLat = null) => set({ selectedEventId: id, selectedEventLngLat: lngLat }),
    setViewport: (viewport) => set({ viewport }),
}))