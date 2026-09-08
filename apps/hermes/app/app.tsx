import { useState } from 'react'
import { MapView } from '@hermes/feature-map'
import { QueryClient, QueryClientProvider, } from '@tanstack/react-query'
import { BootSequence } from '@hermes/ui-components'

const queryClient = new QueryClient()

export function App() {
  const [isBooted, setIsBooted] = useState(false)

  return (
    <QueryClientProvider client={queryClient}>
      <main className="relative w-full h-full overflow-hidden bg-black">
        {!isBooted && <BootSequence onComplete={() => setIsBooted(true)} />}
        <MapView />
      </main>
    </QueryClientProvider>
  );
}

export default App
