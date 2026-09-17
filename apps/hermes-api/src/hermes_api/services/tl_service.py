import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_api.db.models.event import Event
from hermes_api.db.models.event_tl import EventTl
from hermes_api.schemas.events import TlEdgeResponse, TlNodeResponse, TlResponse
from hermes_api.services.ai_service import AiService
from hermes_api.services.geocoding_service import GeocodingService
from hermes_api.services.wikipedia_service import (
    enumerate_timeline_pages,
    fetch_page_extracts,
    search_timeline_titles,
)

logger = logging.getLogger(__name__)







class TlService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._ai = AiService()
        self._geocoding = GeocodingService()



    async def _exec_gen(self, event: Event, existing_tl: EventTl) -> TlResponse:
        titles = await search_timeline_titles(event.ai_headline)
        if not titles:
            await self._session.delete(existing_tl)
            await self._session.commit()
            return TlResponse(status="no_content", message=f"No Wikipedia timeline found for '{event.ai_headline}'")
        else:
            main_title = titles[0]
            pages_to_process = await enumerate_timeline_pages(main_title)
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
                            summary=r_node.tl_summary,
                            location=r_node.location_name,
                            latitude=lat,
                            longitude=lng,
                            wikipedia_url=r_node.wikipedia_url
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
            
            all_nodes.sort(key=lambda n: n.date)
            existing_tl.nodes = [n.model_dump() for n in all_nodes]
            existing_tl.edges = [e.model_dump() for e in all_edges]
            existing_tl.topic_summary = "\n\n".join(tl_summaries)
            existing_tl.wikipedia_title = main_title          
            existing_tl.page_count = len(page_extracts)       
            existing_tl.node_count = len(all_nodes)    
            existing_tl.status = "READY"
            existing_tl.updated_at = datetime.now(timezone.utc)
            await self._session.commit()
            return self._build_response_from_existingtl(existing_tl)
            

    def _build_response_from_existingtl(self, tl: EventTl) -> TlResponse:
        return TlResponse(
            status=tl.status,
            nodes=[TlNodeResponse(**n) for n in tl.nodes],
            edges=[TlEdgeResponse(**e) for e in tl.edges],
            tl_summary=tl.topic_summary,
            generated_at=tl.generated_at
        )

    

    async def gen_tl(self, event_id: uuid.UUID, force_refresh: bool = False) -> TlResponse:
        event = await self._session.get(Event, event_id)
        if not event:
            raise ValueError("event not found.")

        stmt = select(EventTl).where(EventTl.event_id == event_id)
        result = await self._session.execute(stmt)
        existing_tl = result.scalar_one_or_none()
        if existing_tl:
            if existing_tl.status == "READY" and not force_refresh:
                return self._build_response(existing_tl)
            elif existing_tl.status == "GENERATING":
                return TlResponse(
                    status="generating",
                    message="Timeline is currently being generated. Please wait..."
                )
            
            existing_tl.status = "GENERATING"
        else:
            existing_tl = EventTl(event_id=event_id, status="GENERATING")
            self._session.add(existing_tl)

        await self._session.commit()
        
        try:
            return await self._excute_generation(event, existing_tl)
        except Exception as e:
            logger.error(f"Failed to generate timeline for event {event_id}: {e}")
            existing_tl.status = "FAILED"
            await self._session.commit()
            return TlResponse(satus="failed", message=f"Error in generating timeline: {str(e)}")
        