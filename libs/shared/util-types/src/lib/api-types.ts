export type VerificationStatus =
  | 'SINGLE_SOURCE'
  | 'CORROBORATED'
  | 'CONFIRMED'
  | 'CONFLICTING'
  | 'UNVERIFIED';

export type SelectionTier = 'PRIMARY' | 'FILLER' | 'DROP';

export type ImpactLevel = 'CRITICAL' | 'MAJOR' | 'MODERATE' | 'MINOR';

export type EventScope = 'GLOBAL' | 'COUNTRY' | 'STATE' | 'CITY' | 'LOCAL';

export type EventRelationshipType =
  | 'CAUSED'
  | 'FOLLOW_UP'
  | 'REACTION'
  | 'RELATED';

export type RelationshipDirection = 'OUTGOING' | 'INCOMING';

export type EventActorKind = 'STATE' | 'ORGANIZATION' | 'PERSON' | 'GROUP';

export type EventActorRole = 'ACTOR' | 'TARGET' | 'PARTICIPANT';

export interface EventActorItem {
  name: string;
  kind: EventActorKind;
  role: EventActorRole;
  location_name: string | null;
  country_code: string | null;
  latitude: number | null;
  longitude: number | null;
}

export interface ArticleResponse {
  id: string;
  title: string;
  url: string;
  published_at: string | null;
  source_name?: string | null;
}

export interface EventRelationshipItem {
  id: string;
  relationship_type: EventRelationshipType;
  direction: RelationshipDirection;
  confidence: number;
  rationale: string;
  related_event_id: string;
  related_headline: string;
  related_category: string;
  related_category_color: string;
  related_location_name: string | null;
  related_latitude: number | null;
  related_longitude: number | null;
  related_importance_score: number;
  related_event_time: string | null;
}

export interface MapRelationshipEdgeResponse {
  id: string;
  source_event_id: string;
  target_event_id: string;
  source_headline: string;
  source_category: string;
  source_category_color: string;
  source_location_name: string | null;
  source_latitude: number;
  source_longitude: number;
  target_headline: string;
  target_category: string;
  target_category_color: string;
  target_location_name: string | null;
  target_latitude: number;
  target_longitude: number;
  relationship_type: EventRelationshipType;
  confidence: number;
  rationale: string;
}

export interface MapEventResponse {
  id: string;
  ai_headline: string;
  category: string;
  category_color: string;
  location_name: string | null;
  latitude: number;
  longitude: number;
  importance_score: number;
  verification_status: VerificationStatus;
  selection_tier: SelectionTier;
  impact_level: ImpactLevel;
  scope: EventScope;
  event_time: string | null;
  article_count: number;
  source_count: number;
  family_count: number;
  independent_origin_count: number;
  relationship_count?: number;
  actors?: EventActorItem[];
  thread_id: string | null;
  thread_name?: string | null;
}

export interface EventResponse {
  id: string;
  ai_headline: string;
  category: string;
  category_color: string;
  location_name: string | null;
  importance_score: number;
  score_breakdown: Record<string, unknown>;
  verification_status: VerificationStatus;
  selection_tier: SelectionTier;
  impact_level: ImpactLevel;
  scope: EventScope;
  article_count: number;
  source_count: number;
  family_count: number;
  independent_origin_count: number;
  relationship_count?: number;
  actors?: EventActorItem[];
  thread_id: string | null;
  thread_name?: string | null;
  status: string;
  event_time: string | null;
  first_reported_at: string;
  last_updated_at: string;
}

export interface EventDetailResponse extends EventResponse {
  ai_summary: string;
  articles: ArticleResponse[];
  relationships?: EventRelationshipItem[];
}

export type ThreadKind = 'DEVELOPING' | 'TOPIC';
export type ThreadStatus = 'ACTIVE' | 'DORMANT' | 'ENDED';

export interface ThreadResponse {
  id: string;
  name: string;
  kind: ThreadKind;
  status: ThreadStatus;
  description: string | null;
  importance: number;
  event_count: number;
  started_at: string | null;
  last_event_at: string | null;
}

export interface ThreadEventResponse {
  id: string;
  ai_headline: string;
  ai_summary: string | null;
  category: string;
  category_color: string;
  impact_level: ImpactLevel;
  importance_score: number;
  verification_status: VerificationStatus;
  location_name: string | null;
  latitude: number | null;
  longitude: number | null;
  first_reported_at: string;
  last_updated_at: string;
}

export interface ThreadDetailResponse extends ThreadResponse {
  events: ThreadEventResponse[];
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

export interface ChatMapContext {
  event_id?: string | null;
  bbox?: ChatBoundingBox | null;
}

export interface ChatRequest {
  message: string;
  thread_id: string;
  retry?: boolean;
  scope?: ChatScope;
  context?: ChatMapContext | null;
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
