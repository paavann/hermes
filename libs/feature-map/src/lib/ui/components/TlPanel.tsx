import { useMapStore } from "../../store/store"
import { useTl } from "../../hooks/useTl"
import { useEffect, useRef, useState } from "react"
import { Feature, FeatureCollection, LineString } from "geojson"

const NODES_SOURCE = 'tl-nodes-source';
const EDGES_SOURCE = 'tl-edges-source';
const NODES_LAYER  = 'tl-nodes-layer';
const EDGES_LAYER  = 'tl-edges-layer';

function buildGeoJson(tlData: NonNullable<ReturnType<typeof useTl>['query']['data']>) {
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
        const src = tlData.nodes.find((n) => n.id === edge.source_node_id);
        const tgt = tlData.nodes.find((n) => n.id === edge.target_node_id);
        if (src?.longitude && src?.latitude && tgt?.longitude && tgt?.latitude) {
            edgesFeatures.push({
                type: 'Feature',
                geometry: {
                    type: 'LineString',
                    coordinates: [
                        [src.longitude, src.latitude],
                        [tgt.longitude, tgt.latitude],
                    ],
                },
                properties: { type: edge.relationship },
            });
        }
    });

    return {
        nodesGeoJson,
        edgesGeoJson: { type: 'FeatureCollection', features: edgesFeatures } as FeatureCollection,
    };
}

function addLayersToMap(map: mapboxgl.Map) {
    if (!map.getSource(EDGES_SOURCE)) {
        map.addSource(EDGES_SOURCE, { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
    }
    if (!map.getSource(NODES_SOURCE)) {
        map.addSource(NODES_SOURCE, { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
    }
    if (!map.getLayer(EDGES_LAYER)) {
        map.addLayer({
            id: EDGES_LAYER,
            type: 'line',
            source: EDGES_SOURCE,
            paint: {
                'line-color': '#00f0ff',
                'line-width': 2,
                'line-opacity': 0.6,
                'line-dasharray': [2, 2],
            },
        });
    }
    if (!map.getLayer(NODES_LAYER)) {
        map.addLayer({
            id: NODES_LAYER,
            type: 'circle',
            source: NODES_SOURCE,
            paint: {
                // 'coalesce' returns the first non-null value — the correct Mapbox idiom for
                // "use this property if set, else fall back". The ['!=', ..., null] pattern
                // does NOT work for JSON null properties in Mapbox GL JS.
                'circle-color': ['coalesce', ['get', 'category_color'], '#00f0ff'],
                // 'to-boolean' converts null → false, any non-empty string → true.
                'circle-radius': ['case', ['to-boolean', ['get', 'category_color']], 10, 6],
                'circle-stroke-width': 2,
                'circle-stroke-color': '#000000',
            },
        });
    }
}

function removeLayersFromMap(map: mapboxgl.Map) {
    if (map.getLayer(NODES_LAYER)) map.removeLayer(NODES_LAYER);
    if (map.getLayer(EDGES_LAYER)) map.removeLayer(EDGES_LAYER);
    if (map.getSource(NODES_SOURCE)) map.removeSource(NODES_SOURCE);
    if (map.getSource(EDGES_SOURCE)) map.removeSource(EDGES_SOURCE);
}

export function TlPanel({ map }: { map: mapboxgl.Map | null }) {
    const tlTargetId = useMapStore((s) => s.tlTargetId)
    const setTlMode  = useMapStore((s) => s.setTlMode)

    const [activeNodeId, setActiveNodeId] = useState<string | null>(null);

    const { query, regenerate, isRegenerating } = useTl(tlTargetId)
    const { data: tlData, isLoading, isError } = query

    // A new object created on every component mount. Because objects are compared
    // by reference, including this in the dependency array guarantees the effect
    // re-runs every time TlPanel mounts — even when `map` is the same stable ref
    // passed from the parent (which is always the case after the first open).
    const mountId = useRef({});

    // ─── Lifecycle effect: re-runs on every mount of TlPanel ─────────────────
    useEffect(() => {
        if (!map) return;

        const setup = () => {
            // Tear down any stale layers left from a previous session
            removeLayersFromMap(map);
            // Add fresh sources + layers
            addLayersToMap(map);

            // If data is already in cache (second+ open), paint it immediately
            if (tlData?.status === 'READY') {
                const { nodesGeoJson, edgesGeoJson } = buildGeoJson(tlData);
                (map.getSource(NODES_SOURCE) as mapboxgl.GeoJSONSource)?.setData(nodesGeoJson);
                (map.getSource(EDGES_SOURCE) as mapboxgl.GeoJSONSource)?.setData(edgesGeoJson);
            }

            // ── Event handlers ───────────────────────────────────────────────
            const onNodeClick = (e: any) => {
                if (e.features?.[0]) setActiveNodeId(e.features[0].properties.id);
            };
            const onMapClick = (e: any) => {
                const hits = map.queryRenderedFeatures(e.point, { layers: [NODES_LAYER] });
                if (!hits.length) setActiveNodeId(null);
            };
            const onMouseEnter = () => { map.getCanvas().style.cursor = 'pointer'; };
            const onMouseLeave = () => { map.getCanvas().style.cursor = ''; };

            map.on('click', NODES_LAYER, onNodeClick);
            map.on('click', onMapClick);
            map.on('mouseenter', NODES_LAYER, onMouseEnter);
            map.on('mouseleave', NODES_LAYER, onMouseLeave);

            return () => {
                map.off('click', NODES_LAYER, onNodeClick);
                map.off('click', onMapClick);
                map.off('mouseenter', NODES_LAYER, onMouseEnter);
                map.off('mouseleave', NODES_LAYER, onMouseLeave);
                removeLayersFromMap(map);
            };
        };

        const cleanup = setup();

        return () => { if (cleanup) cleanup(); };
    // mountId.current is a new object on every component mount, so this effect
    // reliably re-runs on every TlPanel mount regardless of map ref stability.
    }, [map, mountId.current]); // eslint-disable-line react-hooks/exhaustive-deps

    // ─── Data sync: fires whenever tlData becomes READY ──────────────────────
    useEffect(() => {
        if (!map) return;
        if (tlData?.status !== 'READY') return;
        if (!map.getSource(NODES_SOURCE)) return; // layers not ready yet

        const { nodesGeoJson, edgesGeoJson } = buildGeoJson(tlData);
        (map.getSource(NODES_SOURCE) as mapboxgl.GeoJSONSource).setData(nodesGeoJson);
        (map.getSource(EDGES_SOURCE) as mapboxgl.GeoJSONSource).setData(edgesGeoJson);
    }, [map, tlData]);

    // ─── Styling: active node highlight ──────────────────────────────────────
    useEffect(() => {
        if (!map) return;
        if (!map.getLayer(NODES_LAYER)) return;

        // Active node  → #0c828a (selected teal)
        // Current-event node (has category_color) → its own category color
        // Historical Wikipedia nodes → #00f0ff (timeline cyan)
        // Non-active nodes when something IS selected → dimmed via opacity
        map.setPaintProperty(NODES_LAYER, 'circle-color', [
            'case',
            ['==', ['get', 'id'], activeNodeId ?? ''], '#0c828a',
            ['to-boolean', ['get', 'category_color']], ['get', 'category_color'],
            '#00f0ff',
        ]);
        map.setPaintProperty(NODES_LAYER, 'circle-radius', [
            'case',
            ['==', ['get', 'id'], activeNodeId ?? ''], 12,
            ['to-boolean', ['get', 'category_color']], 10,
            6,
        ]);
        map.setPaintProperty(NODES_LAYER, 'circle-opacity', [
            'case', ['==', ['get', 'id'], activeNodeId ?? ''], 1, activeNodeId ? 0.3 : 1,
        ]);
        if (map.getLayer(EDGES_LAYER)) {
            map.setPaintProperty(EDGES_LAYER, 'line-opacity', activeNodeId ? 0.2 : 0.6);
        }
    }, [map, activeNodeId]);

    // ─── Auto-scroll sidebar entry into view ─────────────────────────────────
    useEffect(() => {
        if (activeNodeId) {
            document.getElementById(`tl-node-${activeNodeId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }, [activeNodeId]);

    const isGenerating = isLoading || isRegenerating || tlData?.status === 'GENERATING';
    const noContent    = tlData?.status === 'no_content';

    return (
        <div className="absolute top-0 right-0 h-screen w-96 bg-hud-bg/95 backdrop-blur-md border-l border-hud-border flex flex-col font-mono z-20 shadow-[0_0_30px_rgba(0,0,0,0.8)]">
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
                className="text-gray-400 hover:text-white cursor-pointer font-bold tracking-widest text-xs disabled:opacity-50"
              >
                REFRESH
              </button>
              <button
                onClick={() => setTlMode(false)}
                className="text-red-500 hover:text-red-400 cursor-pointer font-bold tracking-widest text-xs"
              >
                EXIT
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
              <div className="text-neon-blue text-xs tracking-widest animate-pulse border border-neon-blue/30 p-4 bg-neon-blue/5 text-center mt-4 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                GENERATING TIMELINE...
              </div>
            )}

            {noContent && !isGenerating && !isError && (
              <div className="text-gray-400 text-xs tracking-widest border border-hud-border p-4 bg-black/30 text-center mt-4 leading-relaxed">
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
                {[...tlData.nodes].reverse().map((node) => {
                  const d = new Date(node.date);
                  const formattedDate = isNaN(d.getTime())
                    ? node.date
                    : new Intl.DateTimeFormat('en-US', { month: 'short', day: '2-digit', year: 'numeric' }).format(d);

                  return (
                    <div
                      key={node.id}
                      id={`tl-node-${node.id}`}
                      className={`relative pl-6 pb-6 border-l border-hud-border/50 cursor-pointer transition-colors group ${
                        activeNodeId === node.id ? 'bg-white/10' : 'hover:bg-white/5'
                      }`}
                      onClick={() => {
                        setActiveNodeId(node.id);
                        if (node.longitude && node.latitude) {
                          map?.flyTo({ center: [node.longitude, node.latitude], zoom: 6, duration: 1500 });
                        }
                      }}
                    >
                      <div
                        className={`absolute left-[-5px] top-1 w-[9px] h-[9px] border border-black bg-neon-blue transition-transform shadow-[0_0_10px_rgba(0,240,255,0.4)] ${
                          activeNodeId === node.id ? 'scale-150' : 'group-hover:scale-125'
                        }`}
                      />
                      <div className="text-[10px] text-gray-400 mb-1 flex justify-between">
                        <span className="text-neon-blue font-bold tracking-wider">{formattedDate}</span>
                        {node.location_name && (
                          <span className="truncate max-w-[120px] text-gray-500">{node.location_name}</span>
                        )}
                      </div>
                      <h3 className="text-white text-sm font-bold leading-tight group-hover:text-neon-blue transition-colors mb-2">
                        {node.headline}
                      </h3>
                      <p className="text-gray-400 text-xs leading-relaxed">{node.summary}</p>
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