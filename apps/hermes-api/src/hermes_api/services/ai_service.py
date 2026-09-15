import logging
from typing import Optional
from google import genai
from pydantic import BaseModel, Field

from hermes_api.core.config import settings
from hermes_api.core.constants import PREDEFINED_CATEGORIES



logger = logging.getLogger(__name__)







class LlmResult(BaseModel):
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
        ),
    )

    country_code: Optional[str] = Field(
        default=None,
        description=(
            "The ISO 3166-1 alpha-2 country code. "
            "Examples: 'TR', 'GB', 'US'. Null if has_location is false."
        ),
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
        ),
    )

    matched_event_id: Optional[str] = Field(
        default=None,
        description=(
            "If this article is about the SAME event as one of the "
            "existing events listed below, set this to that event's ID. "
            "Only match if the articles are clearly about the same specific "
            "incident — not just the same general topic. Null if no match."
        ),
    )


class ArticleInput(BaseModel):
    """A single article to include in a batch extraction request."""

    title: str
    content: str


class BatchArticleResult(LlmResult):
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


class TimelineEvent(BaseModel):
    date: str = Field(
        description=(
            "The date of the event in YYYY-MM-DD format if possible. "
            "If exact day is unknown, use YYYY-MM. If only year, use YYYY."
        )
    )
    headline: str = Field(
        description="A concise, neutral, factual headline for the event. Maximum 100 characters."
    )
    summary: str = Field(
        description="A 2-3 sentence summary of the event. Focus on what happened, where, and why it matters."
    )
    location_name: str = Field(
        description=(
            "The most specific place name for where this event happened. "
            "Use the format 'City, Country' when possible. If no specific location "
            "is mentioned, use the most precise region mentioned."
        )
    )


class BatchTimelinePageResult(BaseModel):
    page_index: int = Field(
        description="The 0-based index of the page this result corresponds to from the input list."
    )
    events: list[TimelineEvent] = Field(
        description="The chronological list of events extracted from this page."
    )


class BatchTimelineExtractionResponse(BaseModel):
    results: list[BatchTimelinePageResult] = Field(
        description=(
            "One extraction result per input page. Must contain exactly one "
            "entry for each page provided, identified by page_index."
        )
    )


ARTICLE_BATCH_SIZE: int = 10


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


TIMELINE_SYSTEM_PROMPT = """You are a news historian for Hermes, a geospatial news aggregator.
Your job is to extract a chronological list of structured historical events from Wikipedia timeline prose.

You will receive the text of one or more Wikipedia pages in a single request. Return
exactly one result per input page, using the page_index field to map each result back
to its corresponding input page (0-based).

Rules:
1. Be factual and neutral. Do not editorialize.
2. For location, identify WHERE the event is physically happening. "BBC reports an earthquake in Turkey" → location is Turkey.
3. Extract only the distinct, major events from the prose. Merge tightly related consecutive sentences into a single event.
4. Format dates as YYYY-MM-DD when possible.
"""


def _build_timeline_batch_user_prompt(pages: list[ArticleInput]) -> str:
    """Build a user prompt containing multiple numbered Wikipedia pages."""
    prompt = "# Wikipedia Timeline Pages to analyse\n\n"
    for i, page in enumerate(pages):
        prompt += f"## Page {i}\nTitle: {page.title}\n\nContent:\n{page.content}\n\n"
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
            f"## Article {i}\nTitle: {article.title}\n\nContent:\n{article.content}\n\n"
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


def _resolve_category_color(result: LlmResult) -> LlmResult:
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
        self._model = "gemini-3.1-flash-lite"

    async def get_metadata(
        self,
        articles: list[ArticleInput],
        existing_events: list[dict[str, str]],
    ) -> list[Optional[LlmResult]]:
        """Extract metadata for a batch of articles in a single LLM call.

        Sends all articles to Gemini at once with a batch-aware prompt.
        Each result is mapped back to its input article via article_index.

        Args:
            articles: The batch of articles to extract metadata from.
            existing_events: Active events for deduplication matching.

        Returns:
            An ordered list matching the input articles. Each element
            is an LlmResult on success or None on failure.
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
            results_by_index: dict[int, LlmResult] = {}
            for batch_result in batch_response.results:
                idx = batch_result.article_index
                if idx in results_by_index:
                    logger.warning(
                        f"duplicate article_index {idx} in batch "
                        "response — keeping first."
                    )
                    continue

                resolved = _resolve_category_color(batch_result)
                results_by_index[idx] = resolved

            # Build ordered result list matching input order.
            ordered_results: list[Optional[LlmResult]] = []
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
                        f"no extraction result for article index {i}: '{article.title}'"
                    )
                ordered_results.append(extraction)

            return ordered_results

        except Exception:
            logger.exception(f"batch extraction failed for {len(articles)} articles.")
            return [None] * len(articles)

    async def generate_embeddings(self, texts: list[str]) -> list[Optional[list[float]]]:
        """Generate vector embeddings for a batch of strings using gemini-embedding-001."""
        if not texts:
            return []

        try:
            response = await self._client.aio.models.embed_content(
                model="gemini-embedding-001",
                contents=texts,
                config={"output_dimensionality": 768},
            )
            return [embedding.values for embedding in response.embeddings]

        except Exception:
            logger.exception("failed to generate embeddings")
            # Return None on failure so callers don't crash pgvector with 0 dimensions
            return [None for _ in texts]

    async def extract_timeline_events_batch(
        self,
        pages: list[ArticleInput],
    ) -> list[list[TimelineEvent]]:
        """Extract timeline events for a batch of Wikipedia pages.

        Sends all pages to Gemini at once. Each result is mapped back to its
        input page via page_index. Uses gemini-2.5-flash for complex reasoning.

        Args:
            pages: The batch of pages (title and content) to extract events from.

        Returns:
            An ordered list matching the input pages. Each element is a list
            of TimelineEvent objects extracted from that page.
        """
        if not pages:
            return []

        user_prompt = _build_timeline_batch_user_prompt(pages)

        try:
            res = await self._client.aio.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config={
                    "system_instruction": TIMELINE_SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "response_schema": BatchTimelineExtractionResponse,
                },
            )

            if not res.parsed:
                logger.error(
                    "timeline batch extraction returned no parsed response "
                    f"for {len(pages)} pages."
                )
                return [[] for _ in pages]

            batch_response: BatchTimelineExtractionResponse = res.parsed

            # Map results by page_index
            events_by_index: dict[int, list[TimelineEvent]] = {}
            for batch_result in batch_response.results:
                idx = batch_result.page_index
                if idx in events_by_index:
                    logger.warning(
                        f"duplicate page_index {idx} in timeline batch "
                        "response — keeping first."
                    )
                    continue
                events_by_index[idx] = batch_result.events

            # Build ordered result list matching input order.
            ordered_results: list[list[TimelineEvent]] = []
            for i, page in enumerate(pages):
                events = events_by_index.get(i, [])
                logger.info(
                    f"extracted {len(events)} events from page index {i}: "
                    f"'{page.title}'"
                )
                ordered_results.append(events)

            return ordered_results

        except Exception:
            logger.exception(
                f"timeline batch extraction failed for {len(pages)} pages."
            )
            return [[] for _ in pages]
