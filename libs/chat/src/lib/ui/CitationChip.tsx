import type { ChatSource } from '@hermes/util-types';

import { citationClass, citationTitle } from '../citations';
import type { CitationMarkerSegment } from '../citations';

export interface CitationChipProps {
  segment: CitationMarkerSegment;
  onActivate?: (source: ChatSource) => void;
}

export function CitationChip({
  segment,
  onActivate,
}: CitationChipProps): React.JSX.Element {
  const className = citationClass(segment);
  const title = citationTitle(segment);

  if (!segment.focusable || segment.source === null) {
    return (
      <span className={className} title={title} data-citation={segment.marker}>
        [{segment.marker}]
      </span>
    );
  }

  const source = segment.source;
  return (
    <button
      type="button"
      className={className}
      title={title}
      data-citation={segment.marker}
      aria-label={`Open source: ${source.title}`}
      onClick={() => onActivate?.(source)}
    >
      [{segment.marker}]
    </button>
  );
}
