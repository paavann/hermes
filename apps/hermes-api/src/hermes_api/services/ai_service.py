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








class AiService:
    def __init__(self) -> None:
        self._api_key = settings.LLM_API_KEY
        if not self._api_key:
            logger.error("LLM_API_KEY is missing.")
            raise ValueError("LLM_API_KEY is missing.")

        self._model = settings.LLM_MODEL

        logger.info(f"ai service initialized. Routing set to {self._model} via litellm.")

    