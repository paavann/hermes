import { create } from 'zustand'
import type { MapEventResponse } from '@hermes/util-types'

interface MapState {
    events: MapEventResponse[];
    selectedEventId: string | null;
    isLoading: boolean;
    setEvents: (events: MapEventResponse[]) => void;
    setSelectedEventId: (id: string | null) => void;
    setIsLoading: (isLoading: boolean) => void;
}



export const useMapStore = create<MapState>((set) => ({
    events: [],
    selectedEventId: null,
    isLoading: false,

    setEvents: (events) => set({ events }),
    setSelectedEventId: (id) => set({ selectedEventId: id }),
    setIsLoading: (isLoading) => set({ isLoading })
}))