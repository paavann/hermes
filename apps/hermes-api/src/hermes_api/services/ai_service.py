import logging
from collections.abc import Callable, Sequence
import litellm
from pydantic import BaseModel, Field, field_validator
from hermes_api.core.config import settings
from hermes_api.core.constants import PREDEFINED_CATEGORIES


logger = logging.getLogger(__name__)

ARTICLE_BATCH_SIZE: int = 10


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
    4. Provide a 'tl_summary' (1-2 paragraphs as a plain string,
  never an object or dictionary) summarizing the overarching   
  historical arc of the timeline.
    5. In 'edges', identify causal/thematic relationships      
  between the extracted events (e.g. event 0 triggered event 2).
       Use the 0-based array index of the events you just      
  extracted for source_index and target_index.
"""

TIMELINE_TRIAGE_SYS_PROMPT = """
You are a geopolitical researcher. 
Given a news headline, determine if there is a highly specific, dedicated Wikipedia article that perfectly contextualizes the primary subject of the event.

CRITICAL RULES:
1. BIOGRAPHIES & ENTITIES (ALLOWED): If the headline is about a specific notable person (e.g., dying, resigning), organization, or treaty, return true and use their exact name as the search query.
2. MAJOR CRISES (ALLOWED): If the headline is part of a named, major crisis or war, return true and query the crisis (e.g., "2022 Russian invasion of Ukraine").
3. NO BROAD FALLBACKS (REJECT): If the headline is a routine daily event (e.g., a generic military drill, a minor skirmish, or a political quote), DO NOT fall back to massive, decades-long articles like "North Korea-US relations" or "History of the Middle East". If the specific event or immediate crisis doesn't warrant its own page, set `is_tl_worthy` to false.

If true, provide the exact Wikipedia search query to find the article most specifically tied to the headline's primary subject.
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

    location_name: str | None = Field(
        default=None,
        description="""
            The most specific place name. Format 'City, Country'. Null if has_location is false.
        """,
    )

    country_code: str | None = Field(
        default=None,
        description="""
            ISO 3166-1 alpha-2 country code. Null if has_location is false.
        """,
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
            Use one of these predefined categories if it fits: {", ".join(PREDEFINED_CATEGORIES)}.
            Otherwise UPPER_SNAKE_CASE.
        """
    )

    category_color: str | None = Field(
        default=None,
        description="""
            Hex color code if using a custom category. Null if predefined.
        """,
    )

    matched_event_id: str | None = Field(
        default=None,
        description="""
            If this article is about the SAME exact event as an existing active event, set to its ID.
        """,
    )


class ExtractionResponse(BaseModel):
    events: list[ExtractedEvent] = Field(
        description="One extraction result per input article."
    )


def _coerce_to_str(v: object) -> str:
    """Coerce various LLM output formats (e.g. localized dicts {'en': '...'}) to plain string."""
    if isinstance(v, dict):
        return (
            v.get("en")
            or v.get("text")
            or v.get("summary")
            or v.get("headline")
            or next(
                (
                    str(val)
                    for val in v.values()
                    if isinstance(val, str) and val.strip()
                ),
                "",
            )
            or str(v)
        )
    if isinstance(v, (list, tuple)):
        return " ".join(str(item) for item in v if item is not None)
    if v is None:
        return ""
    return str(v)


class tlNodeExtraction(BaseModel):
    date: str = Field(
        description="""
            the date of the event in YYYY-MM-DD if possible.
        """
    )

    headline: str = Field(
        description="""
            A concise, neutral, factual headline. Max 100 chars.
        """
    )

    location_name: str | None = Field(
        None,
        description="""
            The specific place name (City, Country).
        """,
    )

    summary: str = Field(
        description="""
            A 2-3 sentence summary of the event.
        """
    )

    @field_validator("date", "headline", "summary", mode="before")
    @classmethod
    def coerce_text_fields(cls, v: object) -> str:
        return _coerce_to_str(v)

    @field_validator("location_name", mode="before")
    @classmethod
    def coerce_location_name(cls, v: object) -> str | None:
        if v is None:
            return None
        res = _coerce_to_str(v).strip()
        return res if res else None


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

    @field_validator("relationship", mode="before")
    @classmethod
    def coerce_relationship(cls, v: object) -> str:
        return _coerce_to_str(v)


class TlExtractionResponse(BaseModel):
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
        default_factory=list,
        description="""
            Causal relationships between the extracted nodes.
        """,
    )

    @field_validator("tl_summary", mode="before")
    @classmethod
    def coerce_tl_summary(cls, v: object) -> str:
        return _coerce_to_str(v)


class TimelineSearchQuery(BaseModel):
    is_tl_worthy: bool = Field(
        description="""
            True if this event is part of a major, long-running geopolitical arc (e.g. wars, major diplomatic relations) that would have dedicated Wikipedia coverage.
            False if it is a localized, minor, or isolated incident.
        """
    )

    wiki_search_query: str | None = Field(
        default=None,
        description="""
            If timeline_worthy is true, provide the most relevant Wikipedia search query to find the overarching historical context.
        """,
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


def _build_user_prompt(
    articles: list[ArticleInput], existing_events: list[dict[str, str]]
) -> str:
    prompt = _build_items_prompt(
        articles, header="# Articles to analyse", item_lbl="Article"
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
                "category_color": PREDEFINED_CATEGORIES[category]["color"],
            }
        )
    elif not event.category_color:
        return event.model_copy(update={"category_color": "#6B7280"})
    else:
        return event


def _reidx_results[T, V](
    raw_results: Sequence[T],
    count: int,
    get_idx: Callable[[T], int],
    get_val: Callable[[T], V],
    duplicate_lbl: str,
) -> list[V | None]:
    by_idx: dict[int, V] = {}
    for r in raw_results:
        idx = get_idx(r)
        if idx in by_idx:
            logger.warning("duplicate %s %s in response.", duplicate_lbl, idx)
            continue
        by_idx[idx] = get_val(r)

    return [by_idx.get(i) for i in range(count)]


class AiService:
    def __init__(self) -> None:
        self._primary_model = settings.LLM_MODEL
        self._primary_api_key = settings.LLM_API
        self._fallback_model = settings.LLM_MODEL_1
        self._fallback_api_key = settings.LLM_API_1
        if not self._primary_api_key or not self._primary_model:
            logger.error("primary llm api key or model is missing.")
            raise ValueError("LLM_API or LLM_MODEL is missing.")

        self._embed_api_key = settings.EMBED_API
        self._embed_model = settings.EMBED_MODEL
        if not self._embed_api_key or not self._embed_model:
            logger.error("embed api key or model is missing.")
            raise ValueError("EMBED_API or EMBED_MODEL is missing.")

        model_list = [
            {
                "model_name": "primary-extractor",
                "litellm_params": {
                    "model": self._primary_model,
                    "api_key": self._primary_api_key,
                },
            }
        ]
        fallbacks = []
        if self._fallback_model and self._fallback_api_key:
            model_list.append(
                {
                    "model_name": "fallback-extractor",
                    "litellm_params": {
                        "model": self._fallback_model,
                        "api_key": self._fallback_api_key,
                    },
                }
            )
            fallbacks = [{"primary-extractor": ["fallback-extractor"]}]

        self._router = litellm.Router(
            model_list=model_list,
            fallbacks=fallbacks,
            num_retries=2,
            cooldown_time=180,
            retry_after=True,
        )
        self.router = self._router

        logger.info(
            "ai service initialized. primary=%s, fallback=%s, embed=%s via litellm router.",
            self._primary_model,
            self._fallback_model if fallbacks else "none",
            self._embed_model,
        )

    async def _call_llm(
        self,
        sys_prompt: str,
        user_prompt: str,
        res_model: type[BaseModel],
        schema_name: str,
    ) -> BaseModel | None:
        try:
            res = await self._router.acompletion(
                model="primary-extractor",
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
                logger.warning("llm returned empty content for %s.", schema_name)
                return None
            parsed = res_model.model_validate_json(content)
            return parsed
        except Exception as e:
            logger.error("llm call failed for %s: %s.", schema_name, e)
            return None

    async def get_metadata(
        self, articles: list[ArticleInput], existing_events: list[dict[str, str]]
    ) -> list[ExtractedEvent | None]:
        if not articles:
            return []

        user_prompt = _build_user_prompt(
            articles=articles, existing_events=existing_events or []
        )
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
                logger.info(
                    "extracted: %s... | category = %s.",
                    article.title[:50],
                    extraction.category,
                )
            else:
                logger.warning(
                    "no extraction for article %s: '%s...'.", i, article.title[:120]
                )
        return ordered_results

    async def gen_embeddings(self, texts: list[str]) -> list[list[float] | None]:
        if not texts:
            return []

        try:
            kwargs = {
                "model": self._embed_model,
                "input": texts,
                "api_key": self._embed_api_key,
            }
            if self._embed_model.startswith("nvidia_nim/"):
                kwargs["encoding_format"] = "float"

            res = await litellm.aembedding(**kwargs)
            return [item["embedding"] for item in res.data]
        except Exception as e:
            logger.error("failed to generate embeddings: %s.", e)
            return [None] * len(texts)

    async def extract_tl(
        self, pg_title: str, prose: str
    ) -> TlExtractionResponse | None:
        if not prose.strip():
            return None

        user_prompt = f"# Wikipedia page: {pg_title}\n\n{prose}"
        res = await self._call_llm(
            sys_prompt=TL_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            res_model=TlExtractionResponse,
            schema_name="timeline_extraction",
        )
        if not res:
            logger.warning("failed to extract timeline for %s.", pg_title)
            return None
        else:
            logger.info("timeline extracted successfully for %s.", pg_title)
            return res

    async def analyze_tl_context(self, headline: str) -> TimelineSearchQuery | None:
        user_prompt = f"Headline: {headline}"
        res = await self._call_llm(
            sys_prompt=TIMELINE_TRIAGE_SYS_PROMPT,
            user_prompt=user_prompt,
            res_model=TimelineSearchQuery,
            schema_name="timeline_search_query",
        )

        if isinstance(res, TimelineSearchQuery):
            return res
        else:
            return None
