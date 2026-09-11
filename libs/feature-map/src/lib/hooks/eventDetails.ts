import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import type { EventDetailResponse } from '@hermes/util-types'

import { useMapConfig } from '../config-context'

export function useEventDetails(eventId: string | null) {
    const config = useMapConfig()
    return useQuery({
        queryKey: ['event-details', eventId],
        queryFn: async () => {
            if(!eventId) return null
            const url = `${config.baseUrl}/api/${config.apiVer}/events/${eventId}`
            const res = await axios.get<EventDetailResponse>(url)
            return res.data
        },
        enabled: !!eventId,
        staleTime: 60000,
    })
}