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
}

export interface EventDetailResponse extends EventResponse {
    ai_summary: string;
    articles: ArticleResponse[];
}
