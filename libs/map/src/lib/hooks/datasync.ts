import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

import type { MapEventResponse } from '@hermes/util-types';

import { useMapConfig } from '../config-context';
import { useMapStore } from '../store/store';
import { clampBoundingBox } from './bbox';

export function useMapDataSync() {
  const config = useMapConfig();
  const viewport = useMapStore((state) => state.viewport);

  return useQuery({
    queryKey: ['events', viewport],
    queryFn: async () => {
      if (!viewport) return [];
      const params = clampBoundingBox(viewport);

      const url = `${config.baseUrl}/api/${config.apiVer}/events/bbox`;
      const res = await axios.get<MapEventResponse[]>(url, {
        params,
      });
      return res.data;
    },
    enabled: !!viewport,
    staleTime: 5000,
  });
}
