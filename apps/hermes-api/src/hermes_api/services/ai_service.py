import logging
from typing import Optional
from pydantic import BaseModel, Field
import litellm

from hermes_api.core.config import settings
from hermes_api.core.constants import PREDEFINED_CATEGORIES



logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a news analyst for Hermes, a    
  geospatial news aggregator.
  Your job is to extract structured metadata from news       
  articles so they can be plotted on a world map.
  
  You will receive one or more articles to analyse in a      
  single request. 
  Return exactly one result per input article, using the     
  article_index field to map each result back to its           
  corresponding input article (0-based).
  
  Rules:
  1. Be factual and neutral. Do not editorialize.            
  2. For location, identify WHERE the event is physically    
  happening, not where it was reported from. "BBC reports      
  earthquake in Turkey" -> location is Turkey.
  3. If the article is about an abstract or global topic with
  no specific geographic anchor, set has_location to false.    
  4. For categories, prefer the predefined list. Only create 
  a custom category if none fit.
  5. For event matching, only match if the articles are about
  the EXACT same incident.
"""      








class ArticleInput(BaseModel):
    title: str
    content: str



class ExtractedEvent(BaseModel):
    article_index: int = Field(
        description="The 0-based index of the article this result corresponds to."
    )

    has_location: bool = Field(
        description="""
            True if the article describes an event tied to a specific geographic location.
            False for abstract/global topics.
        """
    )
    
    location_name: Optional[str] = Field(
        default=None,     
        description="""
            The most specific place name. Format 'City, Country'. Null if has_location is false.
        """
    )
    
    country_code: Optional[str] = Field(
        default=None,      
        description="""
            ISO 3166-1 alpha-2 country code. Null if has_location is false.
        """
    )
    
    headline: str = Field(
        description="""
            A concise, neutral, factual headline. Max 100 chars.
        """
    )
    
    summary: str = Field(
        description="""
            A 2-3 sentence summary of the event.
        """
    )
    
    category: str = Field(
        description=f"""
            The event category.
            Use one of these predefined categories if it fits: {', '.join(PREDEFINED_CATEGORIES)}.
            Otherwise UPPER_SNAKE_CASE.
        """
    )
    
    category_color: Optional[str] = Field(
        default=None,    
        description="""
            Hex color code if using a custom category. Null if predefined.
        """
    )
    
    matched_event_id: Optional[str] = Field(
        default=None,  
        description="""
            If this article is about the SAME exact event as an existing active event, set to its ID.
        """
    )



class ExtractionResponse(BaseModel):
    events: list[ExtractedEvent] = Field(
        description="One extraction result per input article."
    )



class EventTl(BaseModel):
    date: str = Field(
        description="""
            The date of the event in YYYY-MM-DD if possible.
        """
    )
    
    headline: str = Field(
        description="""
            A concise, neutral, factual headline. Max 100 chars.
        """
    )
    
    summary: str = Field(
        description="""
            A 2-3 sentence summary of the event.
        """
    )
    
    location_name: str = Field(
        description="""
            The most specific place name. Format 'City, Country'.
        """
    )



class ExtractedEventTl(BaseModel):
    page_index: int = Field(
        description="""
            The 0-based index of the page this result corresponds to.
        """
    )
    
    events: list[EventTl] = Field(
        description="""
            The chronological list of events.
        """
    )



class EventTlExtractionResponse(BaseModel):
    results: list[ExtractedEventTl] = Field(
        description="""
            One extraction result per input page.
        """
    )   







def _build_user_prompt(articles: list[ArticleInput], existing_events: list[dict[str, str]]) -> str:
    prompt = "# Articles to analyse\n\n"
    for i, article in enumerate(articles):
        prompt += (
            f"## Article {i} (index {i})\n"
            f"Title: {article.title}\n"
            f"Content:\n{article.content}\n"
        )

    if existing_events:
        prompt += "# Existing active events (match if applicable)\n\n"
        for event in existing_events:
            prompt += (
                f"ID: {event['id']}\n"
                f"Headline: {event['headline']} |"
                f"Location: {event.get('location_name', 'N/A')} |"
                f"Category: {event['category']}\n"
            )
    else:
        prompt += "# Existing active events\n\nNone currently.\n"
        
    return prompt



def _resolve_category_color(event: ExtractedEvent) -> ExtractedEvent:
    category = event.category.upper()
    if category in PREDEFINED_CATEGORIES:
        return event.model_copy(
            update={
                "category": category,
                "category_color": PREDEFINED_CATEGORIES[category]["color"]
            }
        )
    elif not event.category_color:
        return event.model_copy(update={ "category_color": "#6B7280" })
    else:
        return event





class AiService:
    def __init__(self) -> None:
        self._api_key = settings.LLM_API_KEY
        if not self._api_key:
            logger.error("LLM_API_KEY is missing.")
            raise ValueError("LLM_API_KEY is missing.")

        self._model = settings.LLM_MODEL

        logger.info(f"ai service initialized. Routing set to {self._model} via litellm.")
    

    async def get_metadata(self, articles: list[ArticleInput], existing_events: list[dict[str, str]]) -> list[Optional[ExtractedEvent]]:
        if not articles:
            return []
        
        user_prompt = _build_user_prompt(
            articles=articles,
            existing_events=existing_events or [],
        )
        try:
            res = await litellm.acompletion(
                model=self._model,
                api_key=self._api_key,
                messages=[
                    { "role": "system", "content": SYSTEM_PROMPT },
                    { "role": "user", "content": user_prompt }
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "extraction_response",
                        "schema": ExtractionResponse.model_json_schema()
                    },
                }
            )

            content = res.choices[0].message.content
            if not content:
                logger.error("llm returned empty content.")
                return [None] * len(articles)
            
            batch_response = ExtractionResponse.model_validate_json(content)
            results_by_idx: dict[int, ExtractedEvent] = {}
            for event in batch_response.events:
                idx = event.article_index
                if idx in results_by_idx:
                    logger.warning(f"duplicate article_index {idx} in response.")
                    continue

                results_by_idx[idx] = _resolve_category_color(event)
                
            ordered_results: list[Optional[ExtractedEvent]] = []
            for i, article in enumerate(articles):
                extraction = results_by_idx.get(i)
                if extraction:
                    logger.info(f"extracted: {article.title[:50]}... | category = {extraction.category}.")
                else:
                    logger.warning(f"no extraction for article {i}: '{article.title[:120]}...")
                ordered_results.append(extraction)

            return ordered_results
        except Exception as e:
            logger.error(f"failed to extract metadata: {e}.")
            return [None] * len(articles)
                