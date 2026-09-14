import { useEffect } from 'react';
import { useMapStore } from '../../store/store';
import { useEventLineage } from '../../hooks/eventLineage';
import type { FeatureCollection, Feature, LineString } from 'geojson';

export function LineagePanel({ map }: { map: mapboxgl.Map | null }) {
  const lineageTargetId = useMapStore((s) => s.lineageTargetId);
  const setLineageMode = useMapStore((s) => s.setLineageMode);
  const setSelectedId = useMapStore((s) => s.setSelectedEventId);
  
  const { data: lineageData, isLoading, isError } = useEventLineage(lineageTargetId);

  // Map Integration: Add layers for lineage nodes and edges
  useEffect(() => {
    if (!map || !lineageData) return;
    if (!map.isStyleLoaded()) return;

    // Build Nodes GeoJSON (only for nodes that have lat/lng)
    const nodesGeoJson: FeatureCollection = {
      type: 'FeatureCollection',
      features: lineageData.nodes
        .filter(n => n.latitude !== null && n.longitude !== null)
        .map(n => ({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [n.longitude!, n.latitude!] },
          properties: { ...n }
        }))
    };

    // Build Edges GeoJSON
    const edgesFeatures: Feature<LineString>[] = [];
    lineageData.edges.forEach(edge => {
      const sourceNode = lineageData.nodes.find(n => n.id === edge.source_id);
      const targetNode = lineageData.nodes.find(n => n.id === edge.target_id);
      if (sourceNode?.longitude && sourceNode?.latitude && targetNode?.longitude && targetNode?.latitude) {
        edgesFeatures.push({
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: [
              [sourceNode.longitude, sourceNode.latitude],
              [targetNode.longitude, targetNode.latitude]
            ]
          },
          properties: { type: edge.relationship_type }
        });
      }
    });

    const edgesGeoJson: FeatureCollection = {
      type: 'FeatureCollection',
      features: edgesFeatures
    };

    // Add sources
    if (!map.getSource('lineage-edges-source')) {
      map.addSource('lineage-edges-source', { type: 'geojson', data: edgesGeoJson });
    } else {
      (map.getSource('lineage-edges-source') as mapboxgl.GeoJSONSource).setData(edgesGeoJson);
    }

    if (!map.getSource('lineage-nodes-source')) {
      map.addSource('lineage-nodes-source', { type: 'geojson', data: nodesGeoJson });
    } else {
      (map.getSource('lineage-nodes-source') as mapboxgl.GeoJSONSource).setData(nodesGeoJson);
    }

    // Add layers if they don't exist
    if (!map.getLayer('lineage-edges')) {
      map.addLayer({
        id: 'lineage-edges',
        type: 'line',
        source: 'lineage-edges-source',
        paint: {
          'line-color': '#3b82f6', // neon-blue
          'line-width': 2,
          'line-opacity': 0.6,
          'line-dasharray': [2, 2]
        }
      });
    }

    if (!map.getLayer('lineage-nodes')) {
      map.addLayer({
        id: 'lineage-nodes',
        type: 'circle',
        source: 'lineage-nodes-source',
        paint: {
          'circle-radius': 6,
          'circle-color': ['get', 'category_color'],
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff'
        }
      });
    }

    // Interactions
    const onNodeClick = (e: any) => {
      if (e.features && e.features[0]) {
        const id = e.features[0].properties.id;
        // Fly to and open detail
        setSelectedId(id, [e.lngLat.lng, e.lngLat.lat]);
        setLineageMode(false); // Exit lineage mode to show popup
      }
    };

    const onMouseEnter = () => map.getCanvas().style.cursor = 'pointer';
    const onMouseLeave = () => map.getCanvas().style.cursor = '';

    map.on('click', 'lineage-nodes', onNodeClick);
    map.on('mouseenter', 'lineage-nodes', onMouseEnter);
    map.on('mouseleave', 'lineage-nodes', onMouseLeave);

    return () => {
      map.off('click', 'lineage-nodes', onNodeClick);
      map.off('mouseenter', 'lineage-nodes', onMouseEnter);
      map.off('mouseleave', 'lineage-nodes', onMouseLeave);
      
      if (map.getLayer('lineage-nodes')) map.removeLayer('lineage-nodes');
      if (map.getLayer('lineage-edges')) map.removeLayer('lineage-edges');
      if (map.getSource('lineage-nodes-source')) map.removeSource('lineage-nodes-source');
      if (map.getSource('lineage-edges-source')) map.removeSource('lineage-edges-source');
    };
  }, [map, lineageData, setLineageMode, setSelectedId]);

  return (
    <div className="absolute top-0 left-0 h-screen w-96 bg-hud-bg/95 backdrop-blur-md border-r border-hud-border flex flex-col font-mono z-20 shadow-[0_0_30px_rgba(0,0,0,0.8)]">
      {/* Header */}
      <div className="flex justify-between items-center p-4 border-b border-hud-border bg-black/60">
        <div>
          <h2 className="text-neon-blue font-bold tracking-[0.2em] text-sm uppercase">Lineage Analysis</h2>
          <p className="text-[9px] text-gray-500 tracking-widest mt-1 uppercase">Chronological Thread</p>
        </div>
        <button 
          onClick={() => setLineageMode(false)}
          className="text-red-500 hover:text-red-400 font-bold tracking-widest text-sm"
        >
          [ EXIT ]
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 flex flex-col gap-4">
        {isLoading && <div className="text-neon-blue text-xs tracking-widest animate-pulse">RECONSTRUCTING TIMELINE...</div>}
        {isError && <div className="text-red-500 text-xs tracking-widest">ERROR RECONSTRUCTING TIMELINE</div>}
        
        {lineageData?.nodes.map((node, i) => {
          const d = new Date(node.first_reported_at);
          const formattedDate = new Intl.DateTimeFormat('en-US', { month: 'short', day: '2-digit', year: 'numeric' }).format(d);
          return (
            <div 
              key={node.id} 
              className="relative pl-6 pb-4 border-l border-hud-border/50 cursor-pointer hover:bg-white/5 transition-colors group"
              onClick={() => {
                if(node.longitude && node.latitude) {
                    map?.flyTo({ center: [node.longitude, node.latitude], zoom: 6, duration: 1500 });
                }
              }}
            >
              <div 
                className="absolute left-[-5px] top-1 w-[9px] h-[9px] rounded-full border border-black shadow-[0_0_10px_rgba(255,255,255,0.2)]" 
                style={{ backgroundColor: node.category_color }}
              />
              <div className="text-[10px] text-gray-400 mb-1 flex justify-between">
                <span>{formattedDate}</span>
                {node.location_name && <span className="text-neon-blue truncate max-w-[120px]">{node.location_name}</span>}
              </div>
              <h3 className="text-white text-xs font-bold leading-tight group-hover:text-neon-blue transition-colors">
                {node.ai_headline}
              </h3>
            </div>
          )
        })}
      </div>

      {/* Attribution */}
      <div className="p-3 border-t border-hud-border bg-black/40 text-[9px] text-gray-500 tracking-wider">
        Historical data reconstructed via <a href="https://wikipedia.org" target="_blank" rel="noreferrer" className="text-neon-blue hover:underline">Wikipedia</a> (CC BY-SA).
      </div>
    </div>
  );
}
