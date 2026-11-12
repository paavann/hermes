import type { ChatSource } from '@hermes/util-types';

import { parseCitations } from '../citations';
import { CitationChip } from './CitationChip';

export interface MessageTextProps {
  content: string;
  sources: readonly ChatSource[];
  onCitationActivate?: (source: ChatSource) => void;
}

/** Render assistant text with inline citation chips. */
export function MessageText({
  content,
  sources,
  onCitationActivate,
}: MessageTextProps): React.JSX.Element {
  return (
    <>
      {parseCitations(content, sources).map((segment, index) =>
        segment.type === 'text' ? (
          <span key={`text-${index}`}>{segment.text}</span>
        ) : (
          <CitationChip
            key={`citation-${index}-${segment.marker}`}
            segment={segment}
            onActivate={onCitationActivate}
          />
        ),
      )}
    </>
  );
}
