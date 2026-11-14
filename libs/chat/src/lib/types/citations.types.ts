import type { ChatSource, ChatSourceKind } from '@hermes/util-types'

export type { ChatSource, ChatSourceKind }

export type CitationKind = ChatSourceKind | 'background'

export type CitationMarkerSegment = {
  readonly type: 'citation'
  readonly marker: string
  readonly kind: CitationKind
  readonly source: ChatSource | null
  readonly focusable: boolean
}

export type CitationTextSegment = {
  readonly type: 'text'
  readonly text: string
}

export type CitationSegment = CitationTextSegment | CitationMarkerSegment

export interface CitationRenderOptions {
  onActivate?: (source: ChatSource) => void;
}