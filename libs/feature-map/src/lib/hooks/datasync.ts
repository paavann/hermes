import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useMapStore } from '../store/store';
import type { MapEventResponse } from '@hermes/util-types';

import { useMapConfig } from '../config-context';

export function useMapDataSync() {
  const config = useMapConfig();
  const viewport = useMapStore((state) => state.viewport);

  return useQuery({
    queryKey: ['events', viewport],
    queryFn: async () => {
      if (!viewport) return [];
      let { north, south, east, west } = viewport;

      // Clamp coordinates to valid ranges expected by the backend
      north = Math.min(Math.max(north, -90), 90);
      south = Math.min(Math.max(south, -90), 90);
      east = Math.min(Math.max(east, -180), 180);
      west = Math.min(Math.max(west, -180), 180);

      const url = `${config.baseUrl}/api/${config.apiVer}/events/bbox`;
      const res = await axios.get<MapEventResponse[]>(url, {
        params: { north, south, east, west },
      });
      return res.data;
    },
    enabled: !!viewport,
    staleTime: 5000,
  });
}
