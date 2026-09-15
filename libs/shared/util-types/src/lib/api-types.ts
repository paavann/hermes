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

export interface LineageEdgeResponse {
  source_id: string;
  target_id: string;
  relationship_type: string;
}

export interface LineageNodeResponse {
  id: string;
  ai_headline: string;
  category: string;
  category_color: string;
  location_name: string | null;
  latitude: number | null;
  longitude: number | null;
  trending_score: number;
  article_count: number;
  first_reported_at: string;
}

export interface LineageGraphResponse {
  nodes: LineageNodeResponse[];
  edges: LineageEdgeResponse[];
}
