import logging
from collections.abc import Sequence
from typing import Callable, Optional, TypeVar

import litellm
from pydantic import BaseModel, Field

from hermes_api.core.config import settings
from hermes_api.core.constants import PREDEFINED_CATEGORIES

logger = logging.getLogger(__name__)

ARTICLE_BATCH_SIZE: int = 10

T = TypeVar("T")
V = TypeVar("V")

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

TL_SYSTEM_PROMPT = """You are a geopolitical historian for 
  Hermes, a geospatial news aggregator.
    Your job is to extract a chronological timeline of sub-    
  events from Wikipedia prose, and identify key causal         
  relationships between them.

    Rules:
    1. Extract the major sub-events. Merge tightly related     
  consecutive sentences into a single event.
    2. For 'date', use YYYY-MM-DD if possible.
    3. For 'location_name', identify where the event physically
  happened. If purely political/conceptual without a place,    
  omit it.
    4. Provide a 'topic_summary' (1-2 paragraphs) summarizing  
  the overarching historical arc of the timeline.
    5. In 'edges', identify causal/thematic relationships      
  between the extracted events (e.g. event 0 triggered event 2).
       Use the 0-based array index of the events you just      
  extracted for source_index and target_index.
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



class tlNodeExtraction(BaseModel):
    date: str = Field(
        description="""
            the date of the eventin YYYY-MM-DD if possible.
        """
    )

    headline: str = Field(
        description="""
            A concise, neutral, factual headline. Max 100 chars.
        """
    )

    location_name: Optional[str] = Field(
        None,
        description="""
            The specific place name (City, Country).
        """
    )



class TlEdgeExtraction(BaseModel):
    source_index: int = Field(
        description="""
            The 0-based index of the cause event in the nodes array.
        """
    )

    target_index: int = Field(
        description="""
            The 0-based index of the effect event in the nodes array.
        """
    )

    relationship: str = Field(
        description="""
            A 1-2 word description of the relationship (e.g., 'triggered', 'retaliated').
        """
    )

    
    
class TimelineExtractionResponse(BaseModel):
    tl_summary: str = Field(
        description="""
            A 1-2 paragraph summary of the entire timeline.
        """
    )
    
    nodes: list[tlNodeExtraction] = Field(
        description="""
            The chronological list of events.
        """
    )
    
    edges: list[TlEdgeExtraction] = Field(
        description="""
            Causal relationships between the extracted nodes.
        """
    )








def _build_items_prompt(items: list[ArticleInput], header: str, item_lbl: str) -> str:
    prompt = f"{header}\n\n"
    for i, item in enumerate(items):
        prompt += (
            f"## {item_lbl} {i} (index {i})\n"
            f"Title: {item.title}\n"
            f"Content:\n{item.content}\n"
        )
    return prompt


def _build_user_prompt(articles: list[ArticleInput], existing_events: list[dict[str, str]]) -> str:
    prompt = _build_items_prompt(articles, header="# Articles to analyse", item_lbl="Article")
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


def _reidx_results(raw_results: Sequence[T], count: int, get_idx: Callable[[T], int], get_val: Callable[[T], V], duplicate_lbl: str) -> list[Optional[V]]:
    by_idx: dict[int, V] = {}
    for r in raw_results:
        idx = get_idx(r)
        if idx in by_idx:
            logger.warning(f"duplicate {duplicate_lbl} {idx} in response.")
            continue
        by_idx[idx] = get_val(r)

    return [by_idx.get(i) for i in range(count)]







class AiService:
    def __init__(self) -> None:
        self._api_key = settings.LLM_API_KEY
        self._embed_api_key = settings.EMBED_API_KEY
        if not self._api_key or not self._embed_api_key:
            logger.error("LLM_API_KEY or EMBED_API_KEY is missing.")
            raise ValueError("LLM_API_KEY or EMBED_API_KEY is missing.")

        self._model = settings.LLM_MODEL
        self._embed_model = settings.EMBED_MODEL

        logger.info(f"ai service initialized. Routing set to {self._model} and {self._embed_model} via litellm.")
    


    async def _call_llm(self, sys_prompt: str, user_prompt: str, res_model: type[BaseModel], schema_name: str) -> Optional[BaseModel]:
        try:
            res = await litellm.acompletion(
                model=self._model,
                api_key=self._api_key,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "schema": res_model.model_json_schema(),
                    },
                },
            )

            content = res.choices[0].message.content
            if not content:
                logger.warning(f"llm returned empty content for {schema_name}.")
                return None
            parsed = res_model.model_validate_json(content)
            return parsed
        except Exception as e:
            logger.error(f"llm call failed for {schema_name} {str(e)}")
            return None



    async def get_metadata(self, articles: list[ArticleInput], existing_events: list[dict[str, str]]) -> list[Optional[ExtractedEvent]]:
        if not articles:
            return []
        
        user_prompt = _build_user_prompt(articles=articles, existing_events=existing_events or [])
        res = await self._call_llm(
            sys_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            res_model=ExtractionResponse,
            schema_name="extraction_response",
        )
        if not res:
            return [None] * len(articles)

        ordered_results = _reidx_results(
            raw_results=res.events,  # type: ignore[union-attr]
            count=len(articles),
            get_idx=lambda e: e.article_index,
            get_val=_resolve_category_color,
            duplicate_lbl="article_index",
        ) 
        for i, article in enumerate(articles):
            extraction = ordered_results[i]
            if extraction:
                logger.info(f"extracted: {article.title[:50]}... | category = {extraction.category}.")
            else:
                logger.warning(f"no extraction for article {i}: '{article.title[:120]}...")
        return ordered_results



    async def gen_embeddings(self, texts: list[str]) -> list[Optional[list[float]]]:
        if not texts:
            return []
        
        try:
            res = await litellm.aembedding(
                model=self._embed_model,
                input=texts,
                api_key=self._embed_api_key
            )
            return [item['embedding'] for item in res.data]
        except Exception as e:
            logger.error(f"failed to generate embeddings: {str(e)}")
            return [None] * len(texts)



    async def extract_tl(self, pg_title: str, prose: str) -> Optional[TimelineExtractionResponse]:
        if not prose.strip():
            return None

        user_prompt = f"# Wikipedia page: {pg_title}\n\n{prose}"
        res = await self._call_llm(
            sys_prompt=TL_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            res_model=TimelineExtractionResponse,
            schema_name="timeline_extraction"
        )
        
        if not res:
            logger.warning(f"failed to extract timeline for {pg_title}.")
            return None
        else:
            logger.info(f"timeline extracted successfully for {pg_title}.")
            return res