import logging
from typing import Optional
from google import genai
from pydantic import BaseModel, Field
from hermes_api.core.config import settings
from hermes_api.core.constants import PREDEFINED_CATEGORIES


logger = logging.getLogger(__name__)





class ExtractionResult(BaseModel):
    has_location: bool = Field(
        description=(
            "True if the article describes an event tied to a specific "
            "geographic location. False for abstract/global topics like "
            "'AI regulation debate' or 'stock market trends'."
        )
    )

    location_name: Optional[str] = Field(
        default=None,
        description=(
            "The most specific place name for where this event is "
            "happening. Use the format 'City, Country' when possible. "
            "Examples: 'Ankara, Turkey', 'London, UK'. "
            "Null if has_location is false."
        )
    )

    country_code: Optional[str] = Field(
        default=None,
        description=(
            "The ISO 3166-1 alpha-2 country code. "
            "Examples: 'TR', 'GB', 'US'. Null if has_location is false."
        )
    )

    headline: str = Field(
        description=(
            "A concise, neutral, factual headline for the event. "
            "Maximum 100 characters. Do not editorialize."
        )
    )

    summary: str = Field(
        description=(
            "A 2-3 sentence summary of the event. "
            "Focus on what happened, where, and why it matters."
        )
    )

    category: str = Field(
        description=(
            "The event category. Use one of these predefined categories "
            f"if it fits: {', '.join(PREDEFINED_CATEGORIES)}. "
            "If none fit, use a short custom category name in UPPER_SNAKE_CASE."
        )
    )

    category_color: Optional[str] = Field(
        default=None,
        description=(
            "A hex color code for the category. Only provide this if "
            "the category is NOT one of the predefined ones. "
            "Example: '#7C3AED'. Null if using a predefined category."
        )
    )

    matched_event_id: Optional[str] = Field(
        default=None,
        description=(
            "If this article is about the SAME event as one of the "
            "existing events listed below, set this to that event's ID. "
            "Only match if the articles are clearly about the same specific "
            "incident — not just the same general topic. Null if no match."
        )
    )




SYSTEM_PROMPT = """You are a news analyst for Hermes, a geospatial news aggregator.
Your job is to extract structured metadata from news articles so they can be
plotted on a world map.
Rules:
1. Be factual and neutral. Do not editorialize.
2. For location, identify WHERE the event is physically happening, not where
   it was reported from. "BBC reports earthquake in Turkey" → location is Turkey.
3. If the article is about an abstract or global topic with no specific
   geographic anchor (e.g., "AI ethics debate", "global stock market trends"),
   set has_location to false.
4. For categories, prefer the predefined list. Only create a custom category
   if none of the 10 predefined ones fit.
5. For event matching, only match if the articles are about the EXACT same
   incident. "Turkey earthquake" and "Turkey earthquake aftermath" are the
   same event. "Turkey earthquake" and "Japan earthquake" are NOT.
"""



def _build_user_prompt(title: str, content: str, existing_events: list[dict[str, str]]) -> str:
    prompt = f"# Article to analyse\n\nTitle: {title}\n\nContent:\n{content}\n"
    if existing_events:
        prompt += "\n# Existing active events (match if applicable)\n\n"
        for event in existing_events:
            prompt += (
                f"ID: {event['id']}\n"
                f"Headline: {event['headline']} | "
                f"Location: {event.get('location_name', 'N/A')} | "
                f"Category: {event['category']}\n"
            )
    else:
        prompt += "\n# Existing active events\n\nNone currently.\n"

    return prompt



def _resolve_category_color(result: ExtractionResult) -> ExtractionResult:
    category_upper = result.category.upper()
    if category_upper in PREDEFINED_CATEGORIES:
        return result.model_copy(
            update={
                "category": category_upper,
                "category_color": PREDEFINED_CATEGORIES[category_upper]["color"],
            }
        )
    elif not result.category_color:
        return result.model_copy(update={"category_color": "#6B7280"})
    else:
        return result



class AiService:
    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise ValueError("api key is missing.")
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model = "gemini-3.5-flash-lite"


    async def extract_metadata(self, title: str, content: str, existing_events: list[dict[str, str]]) -> Optional[ExtractionResult]:
        user_prompt = _build_user_prompt(
            title=title, content=content, existing_events=existing_events or [],
        )
        try:
            res = await self._client.aio.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config={
                    "system_instruction": SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "response_schema": ExtractionResult,
                }
            )
            result: ExtractionResult = res.parsed
            result = _resolve_category_color(result)
            logger.info(
                f"extracted: '{result.headline}' | "
                f"category={result.category} | "
                f"location={result.location_name} | "
                f"matched={result.matched_event_id}"
            )

            return result
        except Exception:
            logger.exception(f"failed to extract metadata for article: {title}")
            return None