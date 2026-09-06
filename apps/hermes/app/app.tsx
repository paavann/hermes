import { MapView } from '@hermes/feature-map'
import { QueryClient, QueryClientProvider, } from '@tanstack/react-query'

const queryClient = new QueryClient()



export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <main className="w-full h-full">
        <MapView />
      </main>
    </QueryClientProvider>
  );
}

export default App
