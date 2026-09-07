import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import type { EventDetailResponse } from '@hermes/util-types'



export function useEventDetails(eventId: string | null) {
    return useQuery({
        queryKey: ['event-details', eventId],
        queryFn: async () => {
            if(!eventId) return null
            const res = await axios.get<EventDetailResponse>(
                `http://localhost:8000/api/v1/events/${eventId}`
            )
            return res.data
        },
        enabled: !!eventId,
        staleTime: 60000,
    })
}