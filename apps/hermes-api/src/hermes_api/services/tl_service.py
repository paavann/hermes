import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_api.core.exceptions import (
    EventNotFoundException,
    TlGenErr,
    WikiSearchException,
)
from hermes_api.db.enums import EventTlStatus
from hermes_api.db.models.event import Event
from hermes_api.db.models.event_tl import EventTl
from hermes_api.schemas.events import TlEdgeResponse, TlNodeResponse, TlResponse
from hermes_api.services.ai_service import AiService
from hermes_api.services.geocoding_service import GeocodingService
from hermes_api.services.wikipedia_service import (
    enumerate_tl_pages,
    fetch_page_extracts,
    search_wikipedia,
)
from hermes_api.utils.db import delete_and_commit

logger = logging.getLogger(__name__)







class TlService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._ai = AiService()
        self._geocoding = GeocodingService()



    async def _abort_tl_gen(self, existing_tl: EventTl, status: EventTlStatus, message: str) -> TlResponse:
        await delete_and_commit(self._session, existing_tl)
        return TlResponse(status=status, message=message)



    def _build_response_from_existingtl(self, tl: EventTl) -> TlResponse:
        return TlResponse(
            status=tl.status,
            nodes=[TlNodeResponse(**n) for n in tl.nodes],
            edges=[TlEdgeResponse(**e) for e in tl.edges],
            tl_summary=tl.tl_summary,
            generated_at=tl.generated_at
        )



    async def _exec_gen(self, event: Event, existing_tl: EventTl) -> TlResponse:
        search_context = await self._ai.analyze_tl_context(event.ai_headline)
        if not search_context or not search_context.is_tl_worthy or not search_context.wiki_search_query:
            return await self._abort_tl_gen(existing_tl, EventTlStatus.NO_CONTENT, "Event is not part of a major historical timeline.")

        try:
            titles = await search_wikipedia(search_context.wiki_search_query)
        except WikiSearchException:
            return await self._abort_tl_gen(existing_tl, EventTlStatus.FAILED, f"Wikipedia search failed. Timeline generation aborted for '{event.ai_headline}'.")
        
        if not titles:
            return await self._abort_tl_gen(existing_tl, EventTlStatus.NO_CONTENT, f"No Wikipedia timeline found for '{event.ai_headline}'.")
        else:
            main_title = titles[0]
            pages_to_process = await enumerate_tl_pages(main_title)
            page_extracts = await fetch_page_extracts(pages_to_process)
            all_nodes: list[TlNodeResponse] = []
            all_edges: list[TlEdgeResponse] = []
            tl_summaries: list[str] = []

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
                        geo_res = await self._geocoding.geocode(self._session, r_node.location_name)
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
                            longitude=lng
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
                                relationship=r_edge.relationship
                            )
                        )
            
            if not all_nodes:
                existing_tl.status = EventTlStatus.FAILED
                await self._session.commit()
                return TlResponse(status=EventTlStatus.FAILED, message="AI extraction failed or yielded no results.")
            else:
                all_nodes.sort(key=lambda n: n.date)
                existing_tl.nodes = [n.model_dump() for n in all_nodes]
                existing_tl.edges = [e.model_dump() for e in all_edges]
                existing_tl.tl_summary = "\n\n".join(tl_summaries)
                existing_tl.wikipedia_title = main_title          
                existing_tl.page_count = len(page_extracts)       
                existing_tl.node_count = len(all_nodes)    
                existing_tl.status = EventTlStatus.READY
                existing_tl.generated_at = datetime.now(timezone.utc)
                await self._session.commit()
                return self._build_response_from_existingtl(existing_tl)

    

    async def gen_tl(self, event_id: uuid.UUID, force_refresh: bool = False) -> TlResponse:
        event = await self._session.get(Event, event_id)
        if not event:
            raise EventNotFoundException(event_id)

        stmt = select(EventTl).where(EventTl.event_id == event_id)
        result = await self._session.execute(stmt)
        existing_tl = result.scalar_one_or_none()
        if existing_tl:
            if existing_tl.status == EventTlStatus.READY and not force_refresh:
                return self._build_response_from_existingtl(existing_tl)
            elif existing_tl.status == EventTlStatus.GENERATING:
                return TlResponse(
                    status=EventTlStatus.GENERATING,
                    message="Timeline is currently being generated. Please wait..."
                )
            else:
                existing_tl.status = EventTlStatus.GENERATING
        else:
            existing_tl = EventTl(event_id=event_id, status=EventTlStatus.GENERATING)
            self._session.add(existing_tl)

        await self._session.commit()
        try:
            return await self._exec_gen(event, existing_tl)
        except Exception as e:
            logger.exception("failed to generate timeline for event %s.", event_id)
            existing_tl.status = EventTlStatus.FAILED
            await self._session.commit()
            raise TlGenErr(event_id) from e
        