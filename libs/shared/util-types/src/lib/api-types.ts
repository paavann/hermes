export interface ArticleResponse {
  id: string;
  title: string;
  url: string;
  published_at: string | null;
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
  status: 'READY' | 'GENERATING' | 'no_content';           
  nodes: TlNodeResponse[];
  edges: TlEdgeResponse[];
  tl_summary: string | null;
  generated_at: string | null;
}
