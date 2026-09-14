import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import type { LineageGraphResponse } from '@hermes/util-types'

import { useMapConfig } from '../config-context'

export function useEventLineage(eventId: string | null) {
    const config = useMapConfig()
    return useQuery({
        queryKey: ['event-lineage', eventId],
        queryFn: async () => {
            if(!eventId) return null
            const url = `${config.baseUrl}/api/${config.apiVer}/events/${eventId}/lineage`
            const res = await axios.get<LineageGraphResponse>(url)
            return res.data
        },
        enabled: !!eventId,
        staleTime: 60000,
    })
}
