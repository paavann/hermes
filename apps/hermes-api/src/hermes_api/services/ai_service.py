from geoalchemy2.comparator import BaseComparator
import logging
from typing import Optional, TypeVar, Callable, Sequence
from pydantic import BaseModel, Field
import litellm

from hermes_api.core.config import settings
from hermes_api.core.constants import PREDEFINED_CATEGORIES



logger = logging.getLogger(__name__)

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

TL_SYSTEM_PROMPT = """You are a news historian for Hermes, a geospatial news aggregator.
Your job is to extract a chronological list of structured historical events from Wikipedia timeline prose.
 
You will receive the text of one or more Wikipedia pages in a single request.
Return exactly one result per input page, using the page_index field to map each result back to its corresponding input page (0-based).
 
Rules:
1. Be factual and neutral. Do not editorialize.
2. For location, identify WHERE the event is physically happening. "BBC reports an earthquake in Turkey" -> location is Turkey.
3. Extract only the distinct, major events from the prose. Merge tightly related consecutive sentences into a single event.
4. Format dates as YYYY-MM-DD when possible.
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


def _build_tl_user_prompt(pages: list[ArticleInput]) -> str:
    return _build_items_prompt(pages, header="# Wikipedia Timeline Pages to analyse", item_lbl="Page")



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



    async def get_eventtl(self, pages: list[ArticleInput]) -> list[list[EventTl]]:
        if not pages:
            return []

        user_prompt = _build_tl_user_prompt(pages)
        res = await self._call_llm(
            sys_prompt=TL_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            res_model=EventTlExtractionResponse,
            schema_name="timeline_extraction_response",
        )
        if not res:
            return [[] for _ in pages]

        raw_results = _reidx_results(
            raw_results=res.results,  # type: ignore[union-attr]
            count=len(pages),
            get_idx=lambda r: r.page_index,
            get_val=lambda r: r.events,
            duplicate_lbl="page_index",
        )

        ordered_results: list[list[EventTl]] = [events or [] for events in raw_results]
        for i, page in enumerate(pages):
            logger.info(
                f"extracted {len(ordered_results[i])} timeline events from page {i}: '{page.title[:50]}...'."
            )
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
