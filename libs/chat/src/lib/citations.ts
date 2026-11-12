import { createElement } from 'react';
import type { ReactNode } from 'react';

import type { ChatSource, ChatSourceKind } from '@hermes/util-types';

export type CitationKind = ChatSourceKind | 'background';

export interface CitationTextSegment {
  type: 'text';
  text: string;
}

export interface CitationMarkerSegment {
  type: 'citation';
  marker: string;
  kind: CitationKind;
  source: ChatSource | null;
  focusable: boolean;
}

export type CitationSegment = CitationTextSegment | CitationMarkerSegment;

export interface CitationRenderOptions {
  onActivate?: (source: ChatSource) => void;
}

const MARKER_PATTERN =
  /\[((?:BG|[EATW]\d+)(?:\s*,\s*(?:BG|[EATW]\d+))*)\]/gi;

const KIND_BY_PREFIX: Record<string, ChatSourceKind> = {
  E: 'event',
  A: 'article',
  T: 'timeline',
  W: 'web',
};

const CLICKABLE_CLASS: Record<ChatSourceKind, string> = {
  event:
    'text-neon-blue hover:text-white underline decoration-dotted underline-offset-2 cursor-pointer',
  article:
    'text-neon-blue hover:text-white underline decoration-dotted underline-offset-2 cursor-pointer',
  timeline:
    'text-neon-blue hover:text-white underline decoration-dotted underline-offset-2 cursor-pointer',
  web:
    'text-warning-yellow hover:text-white underline decoration-dotted underline-offset-2 cursor-pointer',
};

const PLAIN_CLASS = 'text-slate-muted cursor-default';
const BACKGROUND_CLASS =
  'text-warning-yellow bg-warning-yellow/10 px-1 cursor-help';

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
  const kind = KIND_BY_PREFIX[marker.charAt(0)];
  return kind ?? null;
}

/**
 * Split answer text into plain text and citation markers.
 *
 * The `sources` event lists cited sources in first-citation order, so the
 * n-th marker of a given kind maps to the n-th source of that kind.
 */
export function parseCitations(
  content: string,
  sources: readonly ChatSource[] = [],
): CitationSegment[] {
  const sourcesByKind: Record<ChatSourceKind, ChatSource[]> = {
    event: [],
    article: [],
    timeline: [],
    web: [],
  };
  for (const source of sources) {
    sourcesByKind[source.kind].push(source);
  }

  const counts: Record<ChatSourceKind, number> = {
    event: 0,
    article: 0,
    timeline: 0,
    web: 0,
  };

  const segments: CitationSegment[] = [];
  let cursor = 0;

  for (const match of content.matchAll(MARKER_PATTERN)) {
    const start = match.index;
    if (start > cursor) {
      segments.push({ type: 'text', text: content.slice(cursor, start) });
    }

    const markerGroup = match[1];
    if (markerGroup === undefined) {
      cursor = start + match[0].length;
      continue;
    }

    for (const rawToken of markerGroup.split(',')) {
      const marker = rawToken.trim().toUpperCase();
      const kind = kindForMarker(marker);
      if (kind === null) {
        segments.push({ type: 'text', text: `[${marker}]` });
        continue;
      }
      if (kind === 'background') {
        segments.push({
          type: 'citation',
          marker,
          kind,
          source: null,
          focusable: false,
        });
        continue;
      }

      const candidates = sourcesByKind[kind];
      const index = counts[kind];
      counts[kind] += 1;
      const source = index < candidates.length ? candidates[index] : null;
      segments.push({
        type: 'citation',
        marker,
        kind,
        source,
        focusable: isFocusableSource(source),
      });
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

export function citationTitle(segment: CitationMarkerSegment): string | undefined {
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
 *
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
