import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useMapConfig } from '../config-context'
import axios from 'axios'
import { TlResponse } from '@hermes/util-types'



export function useTl(eventId: string | null) {
    const config = useMapConfig()
    const queryClient = useQueryClient()
    const queryKey = ['event-timeline', eventId]

    const query = useQuery({
        queryKey,
        queryFn: async () => {
            if(!eventId) {
                return null
            } else {
                const url = `${config.baseUrl}/api/${config.apiVer}/events/tl/${eventId}`
                const res = await axios.post<TlResponse>(url)
                return res.data
            }
        },
        enabled: !!eventId,
        refetchInterval: (query) => {
            if(query.state.data?.status==='GENERATING') {
                return 3000
            } else {
                return false
            }
        },
        staleTime: 60000,
    })

    const regenerateMutation = useMutation({
        mutationFn: async () => {
            if(!eventId) {
                return null
            } else {
                const url = `${config.baseUrl}/api/${config.apiVer}/events/tl/${eventId}?force_refresh=true`
                const res = await axios.post<TlResponse>(url)
                return res.data
            }
        },
        onSuccess: (data) => {
            queryClient.setQueryData(queryKey, data)
        },
    })

    
    return {
        query,
        regenerate: regenerateMutation.mutate,
        isRegenerating: regenerateMutation.isPending,
    }
}