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


class ArticleInput(BaseModel):
    """A single article to include in a batch extraction request."""

    title: str
    content: str


class BatchArticleResult(ExtractionResult):
    """Extraction result for one article within a batch response."""

    article_index: int = Field(
        description=(
            "The 0-based index of the article this result corresponds "
            "to from the input list."
        )
    )


class BatchExtractionResponse(BaseModel):
    """Top-level response schema for batch article extraction."""

    results: list[BatchArticleResult] = Field(
        description=(
            "One extraction result per input article. Must contain "
            "exactly one entry for each article provided, identified "
            "by article_index."
        )
    )


EXTRACTION_BATCH_SIZE: int = 10


SYSTEM_PROMPT = """You are a news analyst for Hermes, a geospatial news aggregator.
Your job is to extract structured metadata from news articles so they can be
plotted on a world map.

You will receive one or more articles to analyse in a single request. Return
exactly one result per input article, using the article_index field to map
each result back to its corresponding input article (0-based).

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



def _build_batch_user_prompt(
    articles: list[ArticleInput],
    existing_events: list[dict[str, str]],
) -> str:
    """Build a user prompt containing multiple numbered articles.

    Each article is labelled with a 0-based index that the LLM must echo
    back in its ``article_index`` response field so results can be mapped
    back to their source articles.

    Args:
        articles: The batch of articles to include in the prompt.
        existing_events: Active events for deduplication matching context.

    Returns:
        The fully formatted user prompt string.
    """
    prompt = "# Articles to analyse\n\n"
    for i, article in enumerate(articles):
        prompt += (
            f"## Article {i}\n"
            f"Title: {article.title}\n\n"
            f"Content:\n{article.content}\n\n"
        )

    if existing_events:
        prompt += "# Existing active events (match if applicable)\n\n"
        for event in existing_events:
            prompt += (
                f"ID: {event['id']}\n"
                f"Headline: {event['headline']} | "
                f"Location: {event.get('location_name', 'N/A')} | "
                f"Category: {event['category']}\n"
            )
    else:
        prompt += "# Existing active events\n\nNone currently.\n"

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

    async def extract_metadata_batch(
        self,
        articles: list[ArticleInput],
        existing_events: list[dict[str, str]],
    ) -> list[Optional[ExtractionResult]]:
        """Extract metadata for a batch of articles in a single LLM call.

        Sends all articles to Gemini at once with a batch-aware prompt.
        Each result is mapped back to its input article via article_index.

        Args:
            articles: The batch of articles to extract metadata from.
            existing_events: Active events for deduplication matching.

        Returns:
            An ordered list matching the input articles. Each element
            is an ExtractionResult on success or None on failure.
        """
        if not articles:
            return []

        user_prompt = _build_batch_user_prompt(
            articles=articles,
            existing_events=existing_events or [],
        )

        try:
            res = await self._client.aio.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config={
                    "system_instruction": SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "response_schema": BatchExtractionResponse,
                },
            )

            if not res.parsed:
                logger.error(
                    "batch extraction returned no parsed response "
                    f"for {len(articles)} articles."
                )
                return [None] * len(articles)

            batch_response: BatchExtractionResponse = res.parsed

            # Map results by article_index, resolve category colors.
            results_by_index: dict[int, ExtractionResult] = {}
            for batch_result in batch_response.results:
                idx = batch_result.article_index
                if idx in results_by_index:
                    logger.warning(
                        f"duplicate article_index {idx} in batch "
                        "response — keeping first."
                    )
                    continue

                resolved = _resolve_category_color(batch_result)
                extraction = ExtractionResult.model_validate(
                    resolved.model_dump(exclude={"article_index"})
                )
                results_by_index[idx] = extraction

            # Build ordered result list matching input order.
            ordered_results: list[Optional[ExtractionResult]] = []
            for i, article in enumerate(articles):
                extraction = results_by_index.get(i)
                if extraction:
                    logger.info(
                        f"extracted: '{extraction.headline}' | "
                        f"category={extraction.category} | "
                        f"location={extraction.location_name} | "
                        f"matched={extraction.matched_event_id}"
                    )
                else:
                    logger.warning(
                        f"no extraction result for article "
                        f"index {i}: '{article.title}'"
                    )
                ordered_results.append(extraction)

            return ordered_results

        except Exception:
            logger.exception(
                "batch extraction failed for "
                f"{len(articles)} articles."
            )
            return [None] * len(articles)

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for a batch of strings using text-embedding-004."""
        if not texts:
            return []
        
        try:
            response = await self._client.aio.models.embed_content(
                model="text-embedding-004",
                contents=texts,
            )
            return [embedding.values for embedding in response.embeddings]
            
        except Exception:
            logger.exception("failed to generate embeddings")
            # Return empty lists or zeroes on failure so callers don't crash
            return [[] for _ in texts]