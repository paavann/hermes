import logging
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING
from hermes_ai.core.constants import (
    ARTICLE_BATCH_SIZE,
    DEFAULT_CATEGORY_COLOR,
    PREDEFINED_CATEGORIES,
)
from hermes_ai.models.events import (
    ArticleInput,
    ExtractedEvent,
    ExtractionResponse,
    GroundedEvent,
)
from hermes_ai.services.geocoding import GeocodingService
from hermes_ai.utils.prompts import ARTICLE_SYSTEM_PROMPT


if TYPE_CHECKING:
    from hermes_ai.client import HermesAiClient

logger = logging.getLogger(__name__)


def _build_events_prompt(
    articles: list[ArticleInput],
    existing_events: list[dict[str, str]] | None = None,
) -> str:
    prompt = "# Articles to analyse\n\n"
    for idx, item in enumerate(articles):
        prompt += (
            f"## Article {idx} (index {idx})\n"
            f"Title: {item.title}\n"
            f"Content:\n{item.content}\n\n"
        )

    if existing_events:
        prompt += "# Existing active events (match if applicable)\n\n"
        for event in existing_events:
            prompt += (
                f"ID: {event.get('id', '')}\n"
                f"Headline: {event.get('headline', '')} | "
                f"Location: {event.get('location_name', 'N/A')} | "
                f"Category: {event.get('category', '')}\n"
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
        return event.model_copy(update={"category_color": DEFAULT_CATEGORY_COLOR})
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


class EventExtractor:
    def __init__(self, client: HermesAiClient) -> None:
        self._client = client

    async def extract_events(
        self,
        articles: list[ArticleInput],
        existing_events: list[dict[str, str]] | None = None,
        geocoding_svc: GeocodingService | None = None,
    ) -> list[ExtractedEvent | None]:
        if not articles:
            return []

        if len(articles) > ARTICLE_BATCH_SIZE:
            all_results: list[ExtractedEvent | None] = []
            for i in range(0, len(articles), ARTICLE_BATCH_SIZE):
                chunk = articles[i : i + ARTICLE_BATCH_SIZE]
                chunk_results = await self.extract_events(
                    articles=chunk,
                    existing_events=existing_events,
                    geocoding_svc=geocoding_svc,
                )
                all_results.extend(chunk_results)
            return all_results

        user_prompt = _build_events_prompt(articles, existing_events)
        res = await self._client.call_llm(
            sys_prompt=ARTICLE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            res_model=ExtractionResponse,
            schema_name="extraction_response",
        )
        if not res:
            return [None] * len(articles)

        ordered = _reidx_results(
            raw_results=res.events,
            count=len(articles),
            get_idx=lambda e: e.article_index,
            get_val=_resolve_category_color,
            duplicate_lbl="article_index",
        )

        final_results: list[ExtractedEvent | None] = []
        for i, article in enumerate(articles):
            extraction = ordered[i]
            if not extraction:
                logger.warning(
                    "no extraction for article %s: '%s...'.", i, article.title[:120]
                )
                final_results.append(None)
                continue

            if geocoding_svc and extraction.has_location and extraction.location_name:
                geo_res = await geocoding_svc.geocode(extraction.location_name)
                grounded = GroundedEvent(
                    article_index=extraction.article_index,
                    has_location=extraction.has_location,
                    location_name=extraction.location_name,
                    country_code=extraction.country_code,
                    headline=extraction.headline,
                    summary=extraction.summary,
                    category=extraction.category,
                    category_color=extraction.category_color,
                    matched_event_id=extraction.matched_event_id,
                    latitude=geo_res.latitude if geo_res else None,
                    longitude=geo_res.longitude if geo_res else None,
                    display_name=geo_res.display_name if geo_res else None,
                )
                final_results.append(grounded)
            else:
                final_results.append(extraction)

            logger.info(
                "extracted: %s... | category = %s.",
                article.title[:50],
                extraction.category,
            )

        return final_results
