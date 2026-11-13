import { useEffect, useRef, useState } from 'react';
import { ArrowsClockwise, X } from '@phosphor-icons/react';
import { cn } from '@hermes/ui-components';

import { useMapStore } from '../../store/store';
import { useTl } from '../../hooks/useTl';
import type { Feature, FeatureCollection, LineString } from 'geojson';
import type { MapLayerMouseEvent, MapMouseEvent } from 'mapbox-gl';

const NODES_SOURCE = 'tl-nodes-source';
const EDGES_SOURCE = 'tl-edges-source';
const NODES_LAYER = 'tl-nodes-layer';
const EDGES_LAYER = 'tl-edges-layer';

function buildGeoJson(
  tlData: NonNullable<ReturnType<typeof useTl>['query']['data']>,
) {
  const nodesGeoJson: FeatureCollection = {
    type: 'FeatureCollection',
    features: tlData.nodes
      .filter(
        (n): n is typeof n & { latitude: number; longitude: number } =>
          n.latitude !== null && n.longitude !== null,
      )
      .map((n) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [n.longitude, n.latitude] },
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
    edgesGeoJson: {
      type: 'FeatureCollection',
      features: edgesFeatures,
    } as FeatureCollection,
  };
}

function addLayersToMap(map: mapboxgl.Map) {
  if (!map.getSource(EDGES_SOURCE)) {
    map.addSource(EDGES_SOURCE, {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });
  }
  if (!map.getSource(NODES_SOURCE)) {
    map.addSource(NODES_SOURCE, {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });
  }
  if (!map.getLayer(EDGES_LAYER)) {
    map.addLayer({
      id: EDGES_LAYER,
      type: 'line',
      source: EDGES_SOURCE,
      paint: {
        'line-color': '#00f0ff',
        'line-width': 1.5,
        'line-opacity': 0.55,
        'line-dasharray': [2, 3],
        'line-emissive-strength': 1,
      },
    });
  }
  if (!map.getLayer(NODES_LAYER)) {
    map.addLayer({
      id: NODES_LAYER,
      type: 'circle',
      source: NODES_SOURCE,
      paint: {
        'circle-color': ['coalesce', ['get', 'category_color'], '#00f0ff'],
        'circle-radius': [
          'case',
          ['to-boolean', ['get', 'category_color']],
          10,
          6,
        ],
        'circle-stroke-width': 1.5,
        'circle-stroke-color': '#07080a',
        'circle-emissive-strength': 1,
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

function formatNodeDate(value: string): { label: string; full: string } {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return { label: value, full: value };
  }
  const full = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
  }).format(date);
  const label = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    year: 'numeric',
  })
    .format(date)
    .toUpperCase();
  return { label, full };
}

export function TlPanel({ map }: { map: mapboxgl.Map | null }) {
  const tlTargetId = useMapStore((s) => s.tlTargetId);
  const setTlMode = useMapStore((s) => s.setTlMode);

  const [activeNodeId, setActiveNodeId] = useState<string | null>(null);

  const { query, regenerate, isRegenerating } = useTl(tlTargetId);
  const { data: tlData, isLoading, isError } = query;

  const mountId = useRef({});

  useEffect(() => {
    if (!map) return;

    const setup = () => {
      removeLayersFromMap(map);
      addLayersToMap(map);

      if (tlData?.status === 'READY') {
        const { nodesGeoJson, edgesGeoJson } = buildGeoJson(tlData);
        (map.getSource(NODES_SOURCE) as mapboxgl.GeoJSONSource)?.setData(
          nodesGeoJson,
        );
        (map.getSource(EDGES_SOURCE) as mapboxgl.GeoJSONSource)?.setData(
          edgesGeoJson,
        );
      }

      const onNodeClick = (e: MapLayerMouseEvent) => {
        if (e.features?.[0]) setActiveNodeId(e.features[0].properties?.id);
      };
      const onMapClick = (e: MapMouseEvent) => {
        const hits = map.queryRenderedFeatures(e.point, {
          layers: [NODES_LAYER],
        });
        if (!hits.length) setActiveNodeId(null);
      };
      const onMouseEnter = () => {
        map.getCanvas().style.cursor = 'pointer';
      };
      const onMouseLeave = () => {
        map.getCanvas().style.cursor = '';
      };

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

    return () => {
      if (cleanup) cleanup();
    };
    // mountId.current is a new object on every component mount, so this effect
    // reliably re-runs on every TlPanel mount regardless of map ref stability.
  }, [map, mountId.current]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!map) return;
    if (tlData?.status !== 'READY') return;
    if (!map.getSource(NODES_SOURCE)) return;

    const { nodesGeoJson, edgesGeoJson } = buildGeoJson(tlData);
    (map.getSource(NODES_SOURCE) as mapboxgl.GeoJSONSource).setData(
      nodesGeoJson,
    );
    (map.getSource(EDGES_SOURCE) as mapboxgl.GeoJSONSource).setData(
      edgesGeoJson,
    );
  }, [map, tlData]);

  useEffect(() => {
    if (!map) return;
    if (!map.getLayer(NODES_LAYER)) return;

    map.setPaintProperty(NODES_LAYER, 'circle-color', [
      'case',
      ['==', ['get', 'id'], activeNodeId ?? ''],
      '#ffb454',
      ['to-boolean', ['get', 'category_color']],
      ['get', 'category_color'],
      '#00f0ff',
    ]);
    map.setPaintProperty(NODES_LAYER, 'circle-radius', [
      'case',
      ['==', ['get', 'id'], activeNodeId ?? ''],
      12,
      ['to-boolean', ['get', 'category_color']],
      10,
      6,
    ]);
    map.setPaintProperty(NODES_LAYER, 'circle-opacity', [
      'case',
      ['==', ['get', 'id'], activeNodeId ?? ''],
      1,
      activeNodeId ? 0.3 : 1,
    ]);
    if (map.getLayer(EDGES_LAYER)) {
      map.setPaintProperty(
        EDGES_LAYER,
        'line-opacity',
        activeNodeId ? 0.2 : 0.55,
      );
    }
  }, [map, activeNodeId]);

  useEffect(() => {
    if (activeNodeId) {
      document
        .getElementById(`tl-node-${activeNodeId}`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [activeNodeId]);

  const isGenerating =
    isLoading || isRegenerating || tlData?.status === 'GENERATING';
  const noContent = tlData?.status === 'NO_CONTENT' && !isGenerating;
  const isFailed = (isError || tlData?.status === 'FAILED') && !isGenerating;

  return (
    <div className="absolute bottom-7 right-0 top-12 z-30 flex w-full flex-col border-l border-border-subtle bg-obsidian font-mono sm:w-[25rem]">
      <div className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-border-subtle bg-black px-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="h-1.5 w-1.5 bg-signal-amber" aria-hidden="true" />
          <div className="min-w-0">
            <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-ivory">
              TIMELINE
            </h2>
            <p className="mt-0.5 truncate text-[8px] uppercase tracking-[0.18em] text-slate-muted/40">
              CAUSAL LINEAGE
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <button
            type="button"
            onClick={() => regenerate()}
            disabled={isGenerating}
            className="flex cursor-pointer items-center gap-1.5 border border-border-subtle bg-onyx px-2 py-1 text-[9px] font-bold uppercase tracking-[0.14em] text-slate-muted/70 transition-colors hover:border-neon-blue hover:text-neon-blue focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2 disabled:cursor-default disabled:opacity-40"
          >
            <ArrowsClockwise size={10} weight="bold" aria-hidden="true" />
            <span>REFRESH</span>
          </button>
          <button
            type="button"
            onClick={() => setTlMode(false)}
            aria-label="Exit timeline"
            className="flex h-7 w-7 cursor-pointer items-center justify-center border border-danger bg-danger text-black transition-colors hover:border-danger-bright hover:bg-danger-bright focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2"
          >
            <X size={12} weight="bold" aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="custom-scrollbar flex flex-1 flex-col gap-4 overflow-y-auto p-4">
        {isFailed ? (
          <div className="border border-danger/40 bg-danger/5 p-4 text-center text-[10px] uppercase leading-relaxed tracking-[0.16em] text-danger-bright">
            ERROR GENERATING TIMELINE.
          </div>
        ) : null}

        {isGenerating && !isFailed ? (
          <div className="flex items-center justify-center gap-2 border border-neon-blue/30 bg-neon-blue/5 p-4 text-[10px] uppercase tracking-[0.16em] text-neon-blue">
            <span className="h-1.5 w-1.5 animate-pulse bg-neon-blue" aria-hidden="true" />
            <span>GENERATING TIMELINE...</span>
          </div>
        ) : null}

        {noContent && !isGenerating && !isFailed ? (
          <div className="border border-border-subtle p-4 text-center text-[10px] uppercase leading-relaxed tracking-[0.14em] text-slate-muted/55">
            NO HISTORICAL CONTEXT FOUND.
            <br />
            <span className="text-slate-muted/35">
              (INSUFFICIENT DATA ON WIKIPEDIA)
            </span>
          </div>
        ) : null}

        {tlData?.status === 'READY' && !isGenerating && !isFailed ? (
          <>
            {tlData.tl_summary ? (
              <div className="border-l-2 border-signal-amber/70 bg-onyx p-3">
                <div className="mb-1.5 text-[8px] uppercase tracking-[0.2em] text-signal-amber/70">
                  LINEAGE SUMMARY
                </div>
                <p className="text-[10px] leading-relaxed text-bone/75">
                  {tlData.tl_summary}
                </p>
              </div>
            ) : null}

            <div className="flex flex-col">
              {[...tlData.nodes].reverse().map((node) => {
                const { full } = formatNodeDate(node.date);
                const isActive = activeNodeId === node.id;

                return (
                  <button
                    key={node.id}
                    id={`tl-node-${node.id}`}
                    type="button"
                    onClick={() => {
                      setActiveNodeId(node.id);
                      if (node.longitude !== null && node.latitude !== null) {
                        map?.flyTo({
                          center: [node.longitude, node.latitude],
                          zoom: 6,
                          duration: 1500,
                        });
                      }
                    }}
                    className={cn(
                      'group relative cursor-pointer border-l py-3.5 pl-5 pr-2 text-left transition-colors focus-visible:outline-1 focus-visible:outline-neon-blue focus-visible:outline-offset-2',
                      isActive
                        ? 'border-neon-blue bg-white/[0.04]'
                        : 'border-border-subtle/60 hover:border-border-bright hover:bg-white/[0.02]',
                    )}
                  >
                    <span
                      className={cn(
                        'absolute -left-[4px] top-4 h-2 w-2 border border-obsidian transition-transform duration-150',
                        isActive
                          ? 'scale-150 bg-signal-amber'
                          : 'bg-neon-blue group-hover:scale-125',
                      )}
                      aria-hidden="true"
                    />

                    <div className="flex items-start justify-between gap-3">
                      <span
                        className={cn(
                          'tabular-nums text-[9px] uppercase tracking-[0.14em]',
                          isActive ? 'text-signal-amber' : 'text-neon-blue/80',
                        )}
                      >
                        {full}
                      </span>
                      {node.location_name ? (
                        <span className="max-w-[9rem] truncate text-[9px] uppercase tracking-[0.1em] text-slate-muted/40">
                          {node.location_name}
                        </span>
                      ) : null}
                    </div>

                    <h3
                      className={cn(
                        'mt-1.5 font-display text-[13px] font-medium leading-snug tracking-[-0.01em] transition-colors',
                        isActive ? 'text-ivory' : 'text-bone/85 group-hover:text-ivory',
                      )}
                    >
                      {node.headline}
                    </h3>
                    <p className="mt-1.5 text-[10px] leading-relaxed text-slate-muted/65">
                      {node.summary}
                    </p>
                  </button>
                );
              })}
            </div>
          </>
        ) : null}
      </div>

      <div className="shrink-0 border-t border-border-subtle bg-black px-3 py-2.5 text-[9px] uppercase tracking-[0.12em] text-slate-muted/40">
        Historical data reconstructed via{' '}
        <a
          href="https://wikipedia.org"
          target="_blank"
          rel="noreferrer"
          className="text-neon-blue/80 transition-colors hover:text-neon-blue hover:underline"
        >
          Wikipedia
        </a>{' '}
        (CC BY-SA).
      </div>
    </div>
  );
}
