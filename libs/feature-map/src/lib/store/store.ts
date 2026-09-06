import { create } from 'zustand'

export interface BoundingBox {
    north: number;
    south: number;
    east: number;
    west: number;
}

interface MapState {
    selectedEventId: string | null;
    viewport: BoundingBox | null;

    setSelectedEventId: (id: string | null) => void;
    setViewport: (viewport: BoundingBox) => void;
}



export const useMapStore = create<MapState>((set) => ({
    selectedEventId: null,
    viewport: null,
    setSelectedEventId: (id) => set({ selectedEventId: id }),
    setViewport: (viewport) => set({ viewport }),
}))