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
    isLineageMode: boolean;
    lineageTargetId: string | null;

    setSelectedEventId: (id: string | null, lngLat?: [number, number]) => void;
    setViewport: (viewport: BoundingBox) => void;
    setLineageMode: (active: boolean, targetId?: string | null) => void;
}

export const useMapStore = create<MapState>((set) => ({
    selectedEventId: null,
    selectedEventLngLat: null,
    viewport: null,
    isLineageMode: false,
    lineageTargetId: null,
    setSelectedEventId: (id, lngLat = null) => set({ selectedEventId: id, selectedEventLngLat: lngLat }),
    setViewport: (viewport) => set({ viewport }),
    setLineageMode: (active, targetId = null) => set({ isLineageMode: active, lineageTargetId: targetId }),
}))