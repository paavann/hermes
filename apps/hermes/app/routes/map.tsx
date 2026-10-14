import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MapView, MapConfigProvider } from '@hermes/map'
import { LiveClock } from '@hermes/ui-components'
import type { MetaFunction } from 'react-router'


const queryClient = new QueryClient()

const MAP_CONFIG = {
  baseUrl: import.meta.env.VITE_BASE_URL,
  apiVer: import.meta.env.VITE_API_VER,
  mapboxToken: import.meta.env.VITE_MAPBOX_TOKEN,
}


export const meta: MetaFunction = () => [
  { title: 'Hermes — Live Intelligence Map' },
  { name: 'description', content: 'Real-time geospatial news intelligence. Monitor global events as they unfold.' },
]


export default function MapRoute() {
  return (
    <QueryClientProvider client={queryClient}>
      <MapConfigProvider config={MAP_CONFIG}>
        <main className="relative w-full overflow-hidden bg-black" style={{ height: '100dvh' }}>
          <MapView />
          <LiveClock />
        </main>
      </MapConfigProvider>
    </QueryClientProvider>
  )
}
