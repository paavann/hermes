import { useState } from 'react'
import { MapView, MapConfigProvider } from '@hermes/feature-map'
import { QueryClient, QueryClientProvider, } from '@tanstack/react-query'
import { BootSequence, LiveClock } from '@hermes/ui-components'

const queryClient = new QueryClient()

const MAP_CONFIG = {
  baseUrl: import.meta.env.VITE_BASE_URL,
  apiVer: import.meta.env.VITE_API_VER,
  mapboxToken: import.meta.env.VITE_MAPBOX_TOKEN,
};

export function App() {
  const [isBooted, setIsBooted] = useState(false)
  console.log("mapbox config: ", MAP_CONFIG)

  return (
    <QueryClientProvider client={queryClient}>
      <MapConfigProvider config={MAP_CONFIG}>
        <main className="relative w-full h-full overflow-hidden bg-black">
          {!isBooted && <BootSequence onComplete={() => setIsBooted(true)} />}
          <MapView />
          <LiveClock />
        </main>
      </MapConfigProvider>
    </QueryClientProvider>
  );
}

export default App
