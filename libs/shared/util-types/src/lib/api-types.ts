export interface ArticleResponse {
  id: string;
  title: string;
  url: string;
  published_at: string | null;
  source_name?: string | null;
}

export interface MapEventResponse {
  id: string;
  ai_headline: string;
  category: string;
  category_color: string;
  location_name: string | null;
  latitude: number;
  longitude: number;
  trending_score: number;
  article_count: number;
  has_lineage?: boolean;
}

export interface EventResponse {
  id: string;
  ai_headline: string;
  category: string;
  category_color: string;
  location_name: string | null;
  trending_score: number;
  article_count: number;
  status: string;
  first_reported_at: string;
  last_updated_at: string;
  has_lineage?: boolean;
}

export interface EventDetailResponse extends EventResponse {
  ai_summary: string;
  articles: ArticleResponse[];
}



export interface TlNodeResponse {
  id: string;
  date: string;
  headline: string;
  summary: string;
  location_name: string | null;
  latitude: number | null;
  longitude: number | null;
  /** Only populated on the terminal "current event" node; null for historical Wikipedia nodes. */
  category_color: string | null;
}

export interface TlEdgeResponse {
  source_node_id: string;
  target_node_id: string;
  relationship: string;
}

export interface TlResponse {
  status: 'READY' | 'GENERATING' | 'NO_CONTENT' | 'FAILED';
  message?: string | null;
  nodes: TlNodeResponse[];
  edges: TlEdgeResponse[];
  tl_summary: string | null;
  generated_at: string | null;
}

export type ChatMessageRole = 'user' | 'assistant';
export type ChatStage =
  | 'accepted'
  | 'planning'
  | 'retrieving'
  | 'searching'
  | 'generating'
  | 'finalizing';
export type ChatSourceKind = 'event' | 'article' | 'timeline' | 'web';
export type ChatCoverageLevel = 'empty' | 'thin' | 'sufficient';
export type ChatGroundingFlag = 'missing_citations';
export type ChatDegradedFlag =
  | 'planner_fallback'
  | 'semantic_unavailable'
  | 'web_unavailable'
  | 'missing_citations';
export type ChatErrorCode =
  | 'RETRIEVAL_FAILED'
  | 'MODEL_TIMEOUT'
  | 'STREAM_TIMEOUT'
  | 'MODEL_FAILED'
  | 'INTERNAL_ERROR'
  | 'CHAT_BUSY';

export interface ChatBoundingBox {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface ChatEventScope {
  type: 'event';
  event_id: string;
}

export interface ChatViewportScope {
  type: 'viewport';
  bbox: ChatBoundingBox;
}

export interface ChatGlobalScope {
  type: 'global';
}

export type ChatScope = ChatEventScope | ChatViewportScope | ChatGlobalScope;

export interface ChatHistoryMessage {
  role: ChatMessageRole;
  content: string;
}

export interface ChatRequest {
  message: string;
  history?: ChatHistoryMessage[];
  scope?: ChatScope;
}

export interface ChatSource {
  kind: ChatSourceKind;
  id: string;
  event_id: string | null;
  title: string;
  url: string | null;
  source_name: string | null;
  published_at: string | null;
  retrieved_at: string | null;
  latitude: number | null;
  longitude: number | null;
  is_external: boolean;
  snippet: string | null;
}

export interface ChatProvenance {
  events: number;
  articles: number;
  timeline_nodes: number;
  web: number;
  background: boolean;
  grounding: ChatGroundingFlag[];
}

export interface ChatUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface ChatCoverage {
  level: ChatCoverageLevel;
  result_count: number;
  best_semantic_similarity: number | null;
  best_lexical_rank: number | null;
  newest_age_hours: number | null;
  recency_stale: boolean;
}

export interface ChatDone {
  provenance: ChatProvenance;
  coverage: ChatCoverage;
  usage: ChatUsage | null;
  web_used: boolean;
  degraded: ChatDegradedFlag[];
}

export interface ChatError {
  code: ChatErrorCode;
  message: string;
  retryable: boolean;
}

export interface ChatStatusEvent {
  type: 'status';
  stage: ChatStage;
}

export interface ChatTokenEvent {
  type: 'token';
  text: string;
}

export interface ChatSourcesEvent {
  type: 'sources';
  sources: ChatSource[];
}

export interface ChatDoneEvent extends ChatDone {
  type: 'done';
}

export interface ChatErrorEvent extends ChatError {
  type: 'error';
}

export type ChatStreamEvent =
  | ChatStatusEvent
  | ChatTokenEvent
  | ChatSourcesEvent
  | ChatDoneEvent
  | ChatErrorEvent;
