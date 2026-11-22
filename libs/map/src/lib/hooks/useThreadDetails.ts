import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import type { ThreadDetailResponse } from '@hermes/util-types';

import { useMapConfig } from '../config-context';

export function useThreadDetails(threadId: string | null) {
  const config = useMapConfig();
  return useQuery({
    queryKey: ['thread-details', threadId],
    queryFn: async () => {
      if (!threadId) return null;
      const url = `${config.baseUrl}/api/${config.apiVer}/threads/${threadId}`;
      const res = await axios.get<ThreadDetailResponse>(url);
      return res.data;
    },
    enabled: !!threadId,
    staleTime: 30000,
  });
}
