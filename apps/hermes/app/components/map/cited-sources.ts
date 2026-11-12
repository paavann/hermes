import type { CitedEvent } from '@hermes/map';
import type { ChatSource } from '@hermes/util-types';

/**
 * Convert chat sources into the unique plotted events behind the citation
 * highlight rings. Web sources and sources without coordinates are skipped.
 */
export function citedEventsFromSources(
  sources: readonly ChatSource[],
): CitedEvent[] {
  const seen = new Set<string>();
  const cited: CitedEvent[] = [];

  for (const source of sources) {
    if (
      source.event_id === null ||
      source.latitude === null ||
      source.longitude === null ||
      seen.has(source.event_id)
    ) {
      continue;
    }
    seen.add(source.event_id);
    cited.push({
      id: source.event_id,
      latitude: source.latitude,
      longitude: source.longitude,
    });
  }

  return cited;
}
