import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useMapStore } from '../store/store'
import type { MapEventResponse } from '@hermes/util-types'

// const BASE_URL = import.meta.env.VITE_BASE_URL
// const API_VER = import.meta.env.VITE_API_VER



export function useMapDataSync() {
    const viewport = useMapStore((state) => state.viewport)

    return useQuery({
        queryKey: ['events', viewport],
        queryFn: async () => {
            if(!viewport) return []
            console.info("fetching map data for viewport...")
            let { north, south, east, west } = viewport
            
            // Clamp coordinates to valid ranges expected by the backend
            north = Math.min(Math.max(north, -90), 90)
            south = Math.min(Math.max(south, -90), 90)
            east = Math.min(Math.max(east, -180), 180)
            west = Math.min(Math.max(west, -180), 180)

            // const url = `${BASE_URL}/${API_VER}/events/bbox`
            const url = `http://localhost:8000/api/v1/events/bbox`
            const res = await axios.get<MapEventResponse[]>(url, {
                params: { north, south, east, west, }
            })
            return res.data
        },
        enabled: !!viewport,
        staleTime: 5000,
    })
}