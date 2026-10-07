import logging
import litellm
from pydantic import BaseModel, Field, field_validator
from hermes_api.core.config import settings


logger = logging.getLogger(__name__)


TL_SYSTEM_PROMPT = """You are a geopolitical historian for Hermes, a geospatial news aggregator.
Your job is to extract a chronological timeline of sub-events from Wikipedia prose, and identify key causal relationships between them.

Rules:
1. Extract the major sub-events. Merge tightly related consecutive sentences into a single event.
2. For 'date', use YYYY-MM-DD if possible.
3. For 'location_name', identify where the event physically happened. If purely political/conceptual without a place, omit it.
4. Provide a 'tl_summary' (1-2 paragraphs as a plain string, never an object or dictionary) summarizing the overarching historical arc of the timeline.
5. In 'edges', identify causal/thematic relationships between the extracted events (e.g. event 0 triggered event 2).
   Use the 0-based array index of the events you just extracted for source_index and target_index.
"""

TIMELINE_TRIAGE_SYS_PROMPT = """You are a geopolitical researcher. 
Given a news headline, determine if there is a highly specific, dedicated Wikipedia article that perfectly contextualizes the primary subject of the event.

CRITICAL RULES:
1. BIOGRAPHIES & ENTITIES (ALLOWED): If the headline is about a specific notable person (e.g., dying, resigning), organization, or treaty, return true and use their exact name as the search query.
2. MAJOR CRISES (ALLOWED): If the headline is part of a named, major crisis or war, return true and query the crisis (e.g., "2022 Russian invasion of Ukraine").
3. NO BROAD FALLBACKS (REJECT): If the headline is a routine daily event (e.g., a generic military drill, a minor skirmish, or a political quote), DO NOT fall back to massive, decades-long articles like "North Korea-US relations" or "History of the Middle East". If the specific event or immediate crisis doesn't warrant its own page, set `is_tl_worthy` to false.

If true, provide the exact Wikipedia search query to find the article most specifically tied to the headline's primary subject.
"""


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


class AiService:
    def __init__(self) -> None:
        self._primary_model = settings.LLM_MODEL
        self._primary_api_key = settings.LLM_API
        self._fallback_model = settings.LLM_MODEL_1
        self._fallback_api_key = settings.LLM_API_1
        if not self._primary_api_key or not self._primary_model:
            logger.error("primary llm api key or model is missing.")
            raise ValueError("LLM_API or LLM_MODEL is missing.")

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
            "ai service initialized. primary=%s, fallback=%s via litellm router.",
            self._primary_model,
            self._fallback_model if fallbacks else "none",
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
