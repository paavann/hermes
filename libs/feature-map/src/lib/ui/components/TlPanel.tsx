import { useMapStore } from "../../store/store"
import { useTl } from "../../hooks/useTl"
import { useEffect } from "react"
import { Feature, FeatureCollection, LineString } from "geojson"

export function TlPanel({ map }: { map: mapboxgl.Map | null }) {
    const tlTargetId = useMapStore((s) => s.tlTargetId)
    const setTlMode = useMapStore((s) => s.setTlMode)
    const setSelectedId = useMapStore((s) => s.setSelectedEventId)

    const { query, regenerate, isRegenerating } = useTl(tlTargetId)
    const { data: tlData, isLoading, isError } = query

    

    useEffect(() => {
        if(!map || !tlData || tlData.status !== 'READY') return;
        if(!map.isStyleLoaded()) return;

        const nodesGeoJson: FeatureCollection = {
            type: 'FeatureCollection',
            features: tlData.nodes
                .filter((n) => n.latitude !== null && n.longitude !== null)
                .map((n) => ({
                type: 'Feature',
                geometry: { type: 'Point', coordinates: [n.longitude!, n.latitude!] },
                properties: { ...n },
                })),
        };

        const edgesFeatures: Feature<LineString>[] = [];
        tlData.edges.forEach((edge) => {
            const sourceNode = tlData.nodes.find((n) => n.id === edge.source_id);
            const targetNode = tlData.nodes.find((n) => n.id === edge.target_id);
            if(sourceNode?.longitude && sourceNode?.latitude && targetNode?.longitude && targetNode?.latitude) {
                edgesFeatures.push({
                    type: 'Feature',
                    geometry: {
                        type: 'LineString',
                        coordinates: [
                            [sourceNode.longitude, sourceNode.latitude],
                            [targetNode.longitude, targetNode.latitude],
                        ],
                    },
                    properties: { type: edge.relationship },
                });
            }
        });

        const edgesGeoJson: FeatureCollection = {
            type: 'FeatureCollection',
            features: edgesFeatures,
        };

        if(!map.getSource('timeline-edges-source')) {
            map.addSource('timeline-edges-source', {
                type: 'geojson',
                data: edgesGeoJson,
            });
        } else {
          (map.getSource('timeline-edges-source') as mapboxgl.GeoJSONSource).setData(edgesGeoJson);
        }

        if(!map.getSource('timeline-nodes-source')) {
            map.addSource('timeline-nodes-source', {
                type: 'geojson',
                data: nodesGeoJson,
            });
        } else {
          (map.getSource('timeline-nodes-source') as mapboxgl.GeoJSONSource).setData(nodesGeoJson);
        }

        if(!map.getLayer('timeline-edges')) {
            map.addLayer({
                id: 'timeline-edges',
                type: 'line',
                source: 'timeline-edges-source',
                paint: {
                    'line-color': '#00f0ff',
                    'line-width': 2,
                    'line-opacity': 0.6,
                    'line-dasharray': [2, 2],
                },
            });
        }

        if (!map.getLayer('timeline-nodes')) {
            map.addLayer({
                id: 'timeline-nodes',
                type: 'circle',
                source: 'timeline-nodes-source',
                paint: {
                    'circle-radius': 6,
                    'circle-color': '#00f0ff',
                    'circle-stroke-width': 2,
                    'circle-stroke-color': '#000000',
                },
            });
        }
        const onNodeClick = (e: any) => {
            if(e.features && e.features[0]) {
                const id = e.features[0].properties.id;
                setSelectedId(id, [e.lngLat.lng, e.lngLat.lat]);
            }
        };
  
        const onMouseEnter = () => (map.getCanvas().style.cursor = 'pointer');
        const onMouseLeave = () => (map.getCanvas().style.cursor = '');
  
        map.on('click', 'timeline-nodes', onNodeClick);
        map.on('mouseenter', 'timeline-nodes', onMouseEnter);
        map.on('mouseleave', 'timeline-nodes', onMouseLeave);

        return () => {
            map.off('click', 'timeline-nodes', onNodeClick);
            map.off('mouseenter', 'timeline-nodes', onMouseEnter);
            map.off('mouseleave', 'timeline-nodes', onMouseLeave);

            if (map.getLayer('timeline-nodes')) map.removeLayer('timeline-nodes');
            if (map.getLayer('timeline-edges')) map.removeLayer('timeline-edges');
            if (map.getSource('timeline-nodes-source')) map.removeSource('timeline-nodes-source');
            if (map.getSource('timeline-edges-source')) map.removeSource('timeline-edges-source');
        };
      }, [map, tlData, setSelectedId]);

    const isGenerating = isLoading || isRegenerating || tlData?.status === 'GENERATING';
    const noContent = tlData?.status === 'no_content';


    return (
        <div className="absolute top-0 left-0 h-screen w-96 bg-hud-bg/95 backdrop-blur-md border-r border-hud-border flex flex-col  
  font-mono z-20 shadow-[0_0_30px_rgba(0,0,0,0.8)]">
          {/* Header */}
          <div className="flex justify-between items-center p-4 border-b border-hud-border bg-black/60">
            <div>
              <h2 className="text-neon-blue font-bold tracking-[0.2em] text-sm uppercase">
                Timeline Analysis
              </h2>
              <p className="text-[9px] text-gray-500 tracking-widest mt-1 uppercase">
                Historical Context
              </p>
            </div>
            <div className="flex gap-4">
              <button
                onClick={() => regenerate()}
                disabled={isGenerating}
                className="text-gray-400 hover:text-white font-bold tracking-widest text-xs disabled:opacity-50"
              >
                [ REGENERATE ]
              </button>
              <button
                onClick={() => setTlMode(false)}
                className="text-red-500 hover:text-red-400 font-bold tracking-widest text-xs"
              >
                [ EXIT ]
              </button>
            </div>
          </div>

                  <div className="flex-1 overflow-y-auto custom-scrollbar p-4 flex flex-col gap-4">
            {isError && (
              <div className="text-red-500 text-xs tracking-widest border border-red-500/30 p-4 bg-red-500/5 text-center mt-4">     
                ERROR RECONSTRUCTING TIMELINE
              </div>
            )}

            {isGenerating && !isError && (
              <div className="text-neon-blue text-xs tracking-widest animate-pulse border border-neon-blue/30 p-4 bg-neon-blue/5    
  text-center mt-4 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                GENERATING TIMELINE...
              </div>
            )}

            {noContent && !isGenerating && !isError && (
              <div className="text-gray-400 text-xs tracking-widest border border-hud-border p-4 bg-black/30 text-center mt-4       
  leading-relaxed">
                NO HISTORICAL CONTEXT FOUND.
                <br />
                (Insufficient data on Wikipedia)
              </div>
            )}
  
            {tlData?.status === 'READY' && !isGenerating && !isError && (
              <>
                {tlData.tl_summary && (
                  <div className="text-gray-300 text-xs italic mb-4 leading-relaxed border-b border-hud-border/50 pb-4">            
                    "{tlData.tl_summary}"
                  </div>
                )}
                {tlData.nodes.map((node) => {
                  const d = new Date(node.date);
                  const formattedDate = isNaN(d.getTime()) 
                    ? node.date
                    : new Intl.DateTimeFormat('en-US', {
                        month: 'short',
                        day: '2-digit',
                        year: 'numeric',
                      }).format(d);
    
                  return (
                    <div
                      key={node.id}
                      className="relative pl-6 pb-6 border-l border-hud-border/50 cursor-pointer hover:bg-white/5 transition-colors 
  group"
                      onClick={() => {
                        if (node.longitude && node.latitude) {
                          map?.flyTo({
                            center: [node.longitude, node.latitude],
                            zoom: 6,
                            duration: 1500,
                          });
                        }
                      }}
                    >
                      <div
                        className="absolute left-[-5px] top-1 w-[9px] h-[9px] border border-black bg-neon-blue group-hover:scale-125
  transition-transform shadow-[0_0_10px_rgba(0,240,255,0.4)]"
                      />
                      <div className="text-[10px] text-gray-400 mb-1 flex justify-between">
                        <span className="text-neon-blue font-bold tracking-wider">{formattedDate}</span>
                        {node.location_name && (
                          <span className="truncate max-w-[120px] text-gray-500">
                            {node.location_name}
                          </span>
                        )}
                      </div>
                      <h3 className="text-white text-sm font-bold leading-tight group-hover:text-neon-blue transition-colors mb-2"> 
                        {node.headline}
                      </h3>
                      <p className="text-gray-400 text-xs leading-relaxed">
                        {node.summary}
                      </p>
                    </div>
                  );
                })}
              </>
            )}
          </div>
  
          {/* Attribution */}
          <div className="p-3 border-t border-hud-border bg-black/40 text-[9px] text-gray-500 tracking-wider">
            Historical data reconstructed via{' '}
            <a
              href="https://wikipedia.org"
              target="_blank"
              rel="noreferrer"
              className="text-neon-blue hover:underline"
            >
              Wikipedia
            </a>{' '}
            (CC BY-SA).
          </div>
        </div>
      );
}