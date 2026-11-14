import { createElement, type ReactNode } from 'react';
import type { ChatSource, ChatSourceKind } from '@hermes/util-types';
import type {
  CitationKind,
  CitationMarkerSegment,
  CitationRenderOptions,
  CitationSegment,
} from './types/citations.types';

export type * from './types/citations.types';

export const CITATION_MARKER_PATTERN =
  /\[((?:BG|[EATW]\d+)(?:\s*,\s*(?:BG|[EATW]\d+))*)\]/gi;

const KIND_BY_PREFIX: Record<string, ChatSourceKind> = {
  E: 'event',
  A: 'article',
  T: 'timeline',
  W: 'web',
};

const BASE_CLICKABLE_CLASS =
  'hover:text-white underline decoration-dotted underline-offset-2 cursor-pointer focus-visible:outline-1 focus-visible:outline-neon-blue';

const CLICKABLE_CLASS: Record<ChatSourceKind, string> = {
  event: `text-neon-blue ${BASE_CLICKABLE_CLASS}`,
  article: `text-neon-blue ${BASE_CLICKABLE_CLASS}`,
  timeline: `text-neon-blue ${BASE_CLICKABLE_CLASS}`,
  web: `text-warning-yellow ${BASE_CLICKABLE_CLASS}`,
};

const PLAIN_CLASS = 'text-slate-muted cursor-default';
const BACKGROUND_CLASS =
  'bg-warning-yellow px-1 font-bold text-black cursor-help';

/** True when activating the citation can move the map or open a URL. */
export function isFocusableSource(source: ChatSource | null): boolean {
  if (source === null) {
    return false;
  }
  if (source.kind === 'web') {
    return source.url !== null;
  }
  return (
    source.event_id !== null &&
    source.latitude !== null &&
    source.longitude !== null
  );
}

function kindForMarker(marker: string): CitationKind | null {
  if (marker === 'BG') {
    return 'background';
  }
  return KIND_BY_PREFIX[marker.charAt(0)] ?? null;
}

function groupSourcesByKind(
  sources: readonly ChatSource[],
): Record<ChatSourceKind, ChatSource[]> {
  const grouped: Record<ChatSourceKind, ChatSource[]> = {
    event: [],
    article: [],
    timeline: [],
    web: [],
  };
  for (const source of sources) {
    grouped[source.kind].push(source);
  }
  return grouped;
}

function parseMarkerToken(
  rawToken: string,
  sourcesByKind: Record<ChatSourceKind, ChatSource[]>,
  counts: Record<ChatSourceKind, number>,
): CitationSegment {
  const marker = rawToken.trim().toUpperCase();
  const kind = kindForMarker(marker);
  if (kind === null) {
    return { type: 'text', text: `[${marker}]` };
  }
  if (kind === 'background') {
    return {
      type: 'citation',
      marker,
      kind,
      source: null,
      focusable: false,
    };
  }
  const index = counts[kind];
  counts[kind] += 1;
  const source = sourcesByKind[kind][index] ?? null;
  return {
    type: 'citation',
    marker,
    kind,
    source,
    focusable: isFocusableSource(source),
  };
}

/**
 * Split answer text into plain text and citation markers.
 * The `sources` event lists cited sources in first-citation order, so the
 * n-th marker of a given kind maps to the n-th source of that kind.
 */
export function parseCitations(
  content: string,
  sources: readonly ChatSource[] = [],
): CitationSegment[] {
  const sourcesByKind = groupSourcesByKind(sources);
  const counts: Record<ChatSourceKind, number> = {
    event: 0,
    article: 0,
    timeline: 0,
    web: 0,
  };
  const segments: CitationSegment[] = [];
  let cursor = 0;

  for (const match of content.matchAll(CITATION_MARKER_PATTERN)) {
    const start = match.index;
    if (start > cursor) {
      segments.push({ type: 'text', text: content.slice(cursor, start) });
    }
    const markerGroup = match[1] ?? '';
    for (const rawToken of markerGroup.split(',')) {
      segments.push(parseMarkerToken(rawToken, sourcesByKind, counts));
    }
    cursor = start + match[0].length;
  }

  if (cursor < content.length) {
    segments.push({ type: 'text', text: content.slice(cursor) });
  }
  return segments;
}

export function citationClass(segment: CitationMarkerSegment): string {
  if (segment.kind === 'background') {
    return BACKGROUND_CLASS;
  }
  if (!segment.focusable) {
    return PLAIN_CLASS;
  }
  return CLICKABLE_CLASS[segment.kind];
}

export function citationTitle(
  segment: CitationMarkerSegment,
): string | undefined {
  if (segment.kind === 'background') {
    return 'Background knowledge, not derived from plotted evidence';
  }
  if (segment.source === null) {
    return 'Source unavailable';
  }
  return segment.source.title;
}

/**
 * Render answer text with inline citation controls.
 * Focusable markers become buttons; background markers are inert; markers
 * without a resolved, focusable source render as plain text.
 */
export function renderCitations(
  content: string,
  sources: readonly ChatSource[],
  { onActivate }: CitationRenderOptions = {},
): ReactNode[] {
  return parseCitations(content, sources).map((segment, index) => {
    if (segment.type === 'text') {
      return segment.text;
    }
    const className = citationClass(segment);
    const title = citationTitle(segment);
    if (!segment.focusable || segment.source === null) {
      return createElement(
        'span',
        {
          key: `citation-${index}`,
          className,
          title,
          'data-citation': segment.marker,
        },
        `[${segment.marker}]`,
      );
    }
    const source = segment.source;
    return createElement(
      'button',
      {
        key: `citation-${index}`,
        type: 'button',
        className,
        title,
        'data-citation': segment.marker,
        'aria-label': `Open source: ${source.title}`,
        onClick: () => {
          onActivate?.(source);
        },
      },
      `[${segment.marker}]`,
    );
  });
}