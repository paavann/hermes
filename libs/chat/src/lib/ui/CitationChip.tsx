import { citationClass, citationTitle } from '../citations'
import type { CitationMarkerSegment } from '../types/citations.types'
import type { ChatSource } from '@hermes/util-types'

export interface CitationChipProps {
  segment: CitationMarkerSegment;
  onActivate?: (source: ChatSource) => void;
}

export function CitationChip({
  segment, onActivate,
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
  const actionLabel =
    segment.kind === 'web'
      ? `Open external source: ${source.title}`
      : `Open source: ${source.title}`;

  return (
    <button
      type="button"
      className={className}
      title={title}
      data-citation={segment.marker}
      aria-label={actionLabel}
      onClick={() => onActivate?.(source)}
    >
      [{segment.marker}]
    </button>
  );
}