import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

import type { UseQueryResult } from '@tanstack/react-query';
import type { MapRelationshipEdgeResponse } from '@hermes/util-types';

import { useMapConfig } from '../config-context';
import { useMapStore } from '../store/store';
import { clampBoundingBox } from './bbox';

export function useMapRelationships(): UseQueryResult<
  MapRelationshipEdgeResponse[]
> {
  const config = useMapConfig();
  const viewport = useMapStore((state) => state.viewport);
  const showRelationships = useMapStore((state) => state.showRelationships);
  const isTlMode = useMapStore((state) => state.isTlMode);

  return useQuery({
    queryKey: ['event-relationships', viewport],
    queryFn: async (): Promise<MapRelationshipEdgeResponse[]> => {
      if (!viewport) return [];
      const params = clampBoundingBox(viewport);
      const url = `${config.baseUrl}/api/${config.apiVer}/events/relationships`;
      const res = await axios.get<MapRelationshipEdgeResponse[]>(url, {
        params,
      });
      return res.data;
    },
    enabled: Boolean(viewport && showRelationships && !isTlMode),
    staleTime: 5000,
  });
}
