import { createContext, useContext, ReactNode } from 'react';

export interface MapConfig {
  baseUrl: string;
  apiVer: string;
  mapboxToken: string;
}

const MapConfigContext = createContext<MapConfig | null>(null);

export function MapConfigProvider({ config, children }: { config: MapConfig, children: ReactNode }) {
  return (
    <MapConfigContext.Provider value={config}>
      {children}
    </MapConfigContext.Provider>
  );
}

export function useMapConfig(): MapConfig {
  const config = useContext(MapConfigContext);
  if (!config) {
    throw new Error('useMapConfig must be used within a MapConfigProvider');
  }
  return config;
}
