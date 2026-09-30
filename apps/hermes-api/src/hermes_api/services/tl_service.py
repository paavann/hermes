import logging
import uuid
from typing import Any
from hermes_db.enums import EventTlStatus
from hermes_db.models import Event, EventTl
from hermes_db.services.tl import EventTlService

from hermes_api.core.exceptions import (
    EventNotFoundException,
    TlGenErr,
    WikiSearchException,
)
from hermes_api.schemas.events import TlEdgeResponse, TlNodeResponse, TlResponse
from hermes_api.services.ai_service import AiService
from hermes_api.services.geocoding_service import GeocodingService
from hermes_api.services.wikipedia_service import (
    enumerate_tl_pages,
    fetch_page_extracts,
    search_wikipedia,
)


logger = logging.getLogger(__name__)


class TlService:
    def __init__(self, tl_db: EventTlService, geocoding: GeocodingService) -> None:
        self._ai = AiService()
        self._geocoding = geocoding
        self._tl_db = tl_db

    async def _abort_tl_gen(
        self, existing_tl: EventTl, status: EventTlStatus, message: str
    ) -> TlResponse:
        await self._tl_db.delete_tl(existing_tl)
        return TlResponse(status=status, message=message)

    def _build_response_from_existingtl(self, tl: EventTl) -> TlResponse:
        return TlResponse(
            status=tl.status,
            nodes=[TlNodeResponse(**n) for n in tl.nodes],
            edges=[TlEdgeResponse(**e) for e in tl.edges],
            tl_summary=tl.tl_summary,
            generated_at=tl.generated_at,
        )

    async def _exec_gen(self, event: Event, existing_tl: EventTl) -> TlResponse:
        search_context = await self._ai.analyze_tl_context(event.ai_headline)
        if (
            not search_context
            or not search_context.is_tl_worthy
            or not search_context.wiki_search_query
        ):
            return await self._abort_tl_gen(
                existing_tl,
                EventTlStatus.NO_CONTENT,
                "Event is not part of a major historical timeline.",
            )

        try:
            titles = await search_wikipedia(search_context.wiki_search_query)
        except WikiSearchException:
            return await self._abort_tl_gen(
                existing_tl,
                EventTlStatus.FAILED,
                f"Wikipedia search failed. Timeline generation aborted for '{event.ai_headline}'.",
            )

        if not titles:
            return await self._abort_tl_gen(
                existing_tl,
                EventTlStatus.NO_CONTENT,
                f"No Wikipedia timeline found for '{event.ai_headline}'.",
            )
        else:
            main_title = titles[0]
            pages_to_process = await enumerate_tl_pages(main_title)
            page_extracts = await fetch_page_extracts(pages_to_process)
            all_nodes: list[TlNodeResponse] = []
            all_edges: list[TlEdgeResponse] = []
            tl_summaries: list[str] = []

            geo_cache: dict[str, Any] = {}
            for page_title, prose in page_extracts.items():
                if not prose.strip():
                    continue

                extraction = await self._ai.extract_tl(page_title, prose)
                if not extraction or not extraction.nodes:
                    continue

                tl_summaries.append(extraction.tl_summary)
                node_id_map: dict[int, str] = {}
                for idx, r_node in enumerate(extraction.nodes):
                    node_id = str(uuid.uuid4())
                    node_id_map[idx] = node_id
                    lat, lng = None, None
                    if r_node.location_name:
                        loc_key = r_node.location_name.strip().lower()
                        if loc_key in geo_cache:
                            geo_res = geo_cache[loc_key]
                        else:
                            geo_res = await self._geocoding.geocode(
                                r_node.location_name
                            )
                            geo_cache[loc_key] = geo_res

                        if geo_res:
                            lat, lng = geo_res.latitude, geo_res.longitude

                    all_nodes.append(
                        TlNodeResponse(
                            id=node_id,
                            date=r_node.date,
                            headline=r_node.headline,
                            summary=r_node.summary,
                            location_name=r_node.location_name,
                            latitude=lat,
                            longitude=lng,
                        )
                    )

                for r_edge in extraction.edges:
                    source_id = node_id_map.get(r_edge.source_index)
                    target_id = node_id_map.get(r_edge.target_index)
                    if source_id and target_id:
                        all_edges.append(
                            TlEdgeResponse(
                                source_node_id=source_id,
                                target_node_id=target_id,
                                relationship=r_edge.relationship,
                            )
                        )

            if not all_nodes:
                await self._tl_db.update_tl_status(existing_tl, EventTlStatus.FAILED)
                return TlResponse(
                    status=EventTlStatus.FAILED,
                    message="AI extraction failed or yielded no results.",
                )
            else:
                all_nodes.sort(key=lambda n: n.date)

                # ── Append the current event as the terminal "today" node ──────────
                # Fetch the event's coordinates via TlDbService
                lat, lng = await self._tl_db.get_event_coordinates(event.id)

                current_node_id = "current-event"
                current_node = TlNodeResponse(
                    id=current_node_id,
                    date=event.last_updated_at.strftime("%Y-%m-%d"),
                    headline=event.ai_headline,
                    summary=event.ai_summary or "",
                    location_name=event.location_name,
                    latitude=lat,
                    longitude=lng,
                    category_color=event.category_color,
                )

                # Connect the previous last node → current event node
                if all_nodes:
                    all_edges.append(
                        TlEdgeResponse(
                            source_node_id=all_nodes[-1].id,
                            target_node_id=current_node_id,
                            relationship="led to",
                        )
                    )
                all_nodes.append(current_node)
                # ──────────────────────────────────────────────────────────────────

                await self._tl_db.save_generated_tl(
                    tl=existing_tl,
                    nodes=[n.model_dump() for n in all_nodes],
                    edges=[e.model_dump() for e in all_edges],
                    tl_summary="\n\n".join(tl_summaries),
                    wikipedia_title=main_title,
                    page_count=len(page_extracts),
                    node_count=len(all_nodes),
                    status=EventTlStatus.READY,
                )
                return self._build_response_from_existingtl(existing_tl)

    async def gen_tl(
        self, event_id: uuid.UUID, force_refresh: bool = False
    ) -> TlResponse:
        event = await self._tl_db.get_event(event_id)
        if not event:
            raise EventNotFoundException(event_id)

        existing_tl = await self._tl_db.get_tl(event_id)
        if existing_tl:
            if existing_tl.status == EventTlStatus.READY and not force_refresh:
                return self._build_response_from_existingtl(existing_tl)
            elif existing_tl.status == EventTlStatus.GENERATING:
                return TlResponse(
                    status=EventTlStatus.GENERATING,
                    message="Timeline is currently being generated. Please wait...",
                )
            else:
                await self._tl_db.update_tl_status(existing_tl, EventTlStatus.GENERATING)
        else:
            existing_tl = await self._tl_db.create_tl(event_id, EventTlStatus.GENERATING)

        try:
            return await self._exec_gen(event, existing_tl)
        except Exception as e:
            logger.exception("failed to generate timeline for event %s.", event_id)
            await self._tl_db.update_tl_status(existing_tl, EventTlStatus.FAILED)
            raise TlGenErr(event_id) from e
