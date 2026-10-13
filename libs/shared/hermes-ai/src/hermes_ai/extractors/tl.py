import logging
from typing import TYPE_CHECKING

from hermes_ai.models.tl import (
    GroundedTlNode,
    TlExtractionResponse,
    TlSearchQuery,
)
from hermes_ai.services.geocoding import GeocodingService
from hermes_ai.utils.prompts import (
    TL_SYSTEM_PROMPT,
    TL_TRIAGE_SYSTEM_PROMPT,
)


if TYPE_CHECKING:
    from hermes_ai.client import HermesAiClient

logger = logging.getLogger(__name__)


class TlExtractor:
    def __init__(self, client: HermesAiClient) -> None:
        self._client = client

    async def extract_tl(
        self,
        pg_title: str,
        prose: str,
        geocoding_svc: GeocodingService | None = None,
    ) -> TlExtractionResponse | None:
        if not prose.strip():
            return None

        user_prompt = f"# Wikipedia page: {pg_title}\n\n{prose}"
        res = await self._client.call_llm(
            sys_prompt=TL_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            res_model=TlExtractionResponse,
            schema_name="timeline_extraction",
        )
        if not res:
            logger.warning("failed to extract timeline for %s.", pg_title)
            return None

        if geocoding_svc:
            grounded_nodes = []
            for node in res.nodes:
                lat, lon = None, None
                if node.location_name:
                    geo_res = await geocoding_svc.geocode(node.location_name)
                    if geo_res:
                        lat, lon = geo_res.latitude, geo_res.longitude
                grounded_nodes.append(
                    GroundedTlNode(
                        date=node.date,
                        headline=node.headline,
                        location_name=node.location_name,
                        summary=node.summary,
                        latitude=lat,
                        longitude=lon,
                    )
                )
            res = TlExtractionResponse(
                tl_summary=res.tl_summary,
                nodes=grounded_nodes,
                edges=res.edges,
            )

        logger.info("timeline extracted successfully for %s.", pg_title)
        return res

    async def analyze_tl_context(self, headline: str) -> TlSearchQuery | None:
        user_prompt = f"Headline: {headline}"
        res = await self._client.call_llm(
            sys_prompt=TL_TRIAGE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            res_model=TlSearchQuery,
            schema_name="timeline_search_query",
        )
        if isinstance(res, TlSearchQuery):
            return res
        return None
