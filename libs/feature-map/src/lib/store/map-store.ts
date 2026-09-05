import { create } from 'zustand'
import type { MapEventResponse } from '@hermes/util-types'

export interface BoundingBox {
    north: number;
    south: number;
    east: number;
    west: number;
}

interface MapState {
    events: MapEventResponse[];
    selectedEventId: string | null;
    isLoading: boolean;
    viewport: BoundingBox | null;
    
    setEvents: (events: MapEventResponse[]) => void;
    setSelectedEventId: (id: string | null) => void;
    setIsLoading: (isLoading: boolean) => void;
    setViewport: (viewport: BoundingBox) => void;
}



export const useMapStore = create<MapState>((set) => ({
    events: [],
    selectedEventId: null,
    isLoading: false,
    viewport: null,

    setEvents: (events) => set({ events }),
    setSelectedEventId: (id) => set({ selectedEventId: id }),
    setIsLoading: (isLoading) => set({ isLoading }),
    setViewport: (viewport) => set({ viewport }),
}))