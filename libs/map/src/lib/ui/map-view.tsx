import { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useMapStore } from '../store/store';
import { useMapDataSync } from '../hooks/datasync';
import { useMapRelationships } from '../hooks/useMapRelationships';
import { CornerReticle } from '@hermes/ui-components';

import { ClusterList } from './components/ClusterList';
import { EventPopup } from './components/EventPopup';
import type { PopupInsets } from './components/EventPopup';
import { StoryPanel } from './components/StoryPanel';
import { TlPanel } from './components/TlPanel';
import { EventsLoader } from './components/EventsLoader';
import { MapHud } from './components/MapHud';
import { createCitedGeoJson } from './cited-geojson';
import { buildActorGeoJson, buildRelationshipGeoJson } from './relationship-geojson';
import { ACTOR_VECTOR_COLOR, RELATIONSHIP_COLORS } from './relationship-theme';
import type { FeatureCollection } from 'geojson';
import type { MapEventResponse } from '@hermes/util-types';
import { useMapConfig } from '../config-context';

export interface MapViewProps {
  readonly threadId?: string | null;
  readonly onThreadChange?: (threadId: string | null) => void;
  readonly popupInsets?: PopupInsets;
}

const createGeoJson = (events: MapEventResponse[]): FeatureCollection => ({
  type: 'FeatureCollection',
  features: [...events]
    .sort((left, right) => right.importance_score - left.importance_score)
    .map((event, index) => ({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [event.longitude, event.latitude],
      },
      properties: {
        ...event,
        rank: index + 1,
      },
    })),
});

export function MapView({
  threadId = null,
  onThreadChange,
  popupInsets,
}: MapViewProps) {
  const config = useMapConfig();
  mapboxgl.accessToken = config.mapboxToken;

  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [isMapReady, setIsMapReady] = useState(false);
  const [hoveredEventId, setHoveredEventId] = useState<string | null>(null);
  const [clusterEvents, setClusterEvents] = useState<MapEventResponse[] | null>(
    null,
  );
  const setViewport = useMapStore((state) => state.setViewport);
  const { data: events, isFetching } = useMapDataSync();
  const { data: relationships } = useMapRelationships();
  const setSelectedId = useMapStore((s) => s.setSelectedEventId);

  const selectedEventId = useMapStore((s) => s.selectedEventId);
  const showRelationships = useMapStore((s) => s.showRelationships);
  const isTimelineMode = useMapStore((s) => s.isTlMode);
  const citedEvents = useMapStore((s) => s.citedEvents);
  const focusRequest = useMapStore((s) => s.focusRequest);
  const activeLinksEventId = isTimelineMode
    ? null
    : (selectedEventId ?? hoveredEventId);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/pavann/cmtvb17eo006j01s727jq81q8',
      center: [0, 20],
      zoom: 1.5,
      projection: 'mercator',
      pitch: 0,
      maxPitch: 0,
      dragRotate: false,
      touchPitch: false,
      attributionControl: false,
      renderWorldCopies: false,
    });

    const updateBounds = () => {
      if (!map.current) return;
      const bounds = map.current.getBounds();
      if (bounds) {
        setViewport({
          north: bounds.getNorthEast().lat,
          south: bounds.getSouthWest().lat,
          east: bounds.getNorthEast().lng,
          west: bounds.getSouthWest().lng,
        });
      }
    };

    map.current.on('load', () => {
      setIsMapReady(true);

      map.current?.on('click', 'hermes-unclustered-point', (e) => {
        if (!map.current) return;
        const rendered = map.current.queryRenderedFeatures(e.point, {
          layers: ['hermes-unclustered-point'],
        });
        const stackedIds = rendered
          .map((feature) => feature.properties?.id)
          .filter((id): id is string => typeof id === 'string');
        if (stackedIds.length === 0) return;

        const currentId = useMapStore.getState().selectedEventId;
        const position = currentId === null ? -1 : stackedIds.indexOf(currentId);
        const eventId = stackedIds[(position + 1) % stackedIds.length];
        const feature = rendered.find(
          (candidate) => candidate.properties?.id === eventId,
        );
        const point = feature?.geometry;
        const lngLat: [number, number] =
          point?.type === 'Point'
            ? [point.coordinates[0], point.coordinates[1]]
            : [e.lngLat.lng, e.lngLat.lat];

        setClusterEvents(null);
        setSelectedId(eventId, lngLat);
        map.current.easeTo({
          center: lngLat,
          duration: 800,
          easing: (t) => t * (2 - t), // smooth ease out
        });
      });
      map.current?.on('mouseenter', 'hermes-unclustered-point', (e) => {
        if (map.current) map.current.getCanvas().style.cursor = 'pointer';
        const hoveredId = e.features?.[0]?.properties?.id;
        if (typeof hoveredId === 'string') {
          setHoveredEventId(hoveredId);
        }
      });
      map.current?.on('mouseleave', 'hermes-unclustered-point', () => {
        if (map.current) map.current.getCanvas().style.cursor = '';
        setHoveredEventId(null);
      });

      map.current?.on('click', 'hermes-cited-points', (e) => {
        if (e.features && e.features[0] && map.current) {
          const eventId = e.features[0].properties?.id;
          if (eventId) {
            const lngLat: [number, number] = [e.lngLat.lng, e.lngLat.lat];
            setSelectedId(eventId, lngLat);

            map.current.easeTo({
              center: lngLat,
              duration: 800,
              easing: (t) => t * (2 - t),
            });
          }
        }
      });
      map.current?.on('mouseenter', 'hermes-cited-points', () => {
        if (map.current) map.current.getCanvas().style.cursor = 'pointer';
      });
      map.current?.on('mouseleave', 'hermes-cited-points', () => {
        if (map.current) map.current.getCanvas().style.cursor = '';
      });

      map.current?.on('click', 'hermes-relationship-partners', (e) => {
        if (e.features && e.features[0] && map.current) {
          const eventId = e.features[0].properties?.id;
          if (typeof eventId === 'string') {
            const point = e.features[0].geometry;
            const lngLat: [number, number] =
              point.type === 'Point'
                ? [point.coordinates[0], point.coordinates[1]]
                : [e.lngLat.lng, e.lngLat.lat];
            setClusterEvents(null);
            setSelectedId(eventId, lngLat);

            map.current.easeTo({
              center: lngLat,
              duration: 800,
              easing: (t) => t * (2 - t),
            });
          }
        }
      });
      map.current?.on('mouseenter', 'hermes-relationship-partners', () => {
        if (map.current) map.current.getCanvas().style.cursor = 'pointer';
      });
      map.current?.on('mouseleave', 'hermes-relationship-partners', () => {
        if (map.current) map.current.getCanvas().style.cursor = '';
      });

      // Cluster inspection: list every member so collocated pins stay reachable.
      map.current?.on('click', 'hermes-clusters', (e) => {
        const features = map.current?.queryRenderedFeatures(e.point, {
          layers: ['hermes-clusters'],
        });
        const clusterFeature = features?.[0];
        if (!clusterFeature || !map.current) return;
        const clusterId = Number(clusterFeature.properties?.cluster_id);
        if (!Number.isFinite(clusterId)) return;

        const source = map.current.getSource(
          'events-source',
        ) as mapboxgl.GeoJSONSource | undefined;
        if (!source) return;

        source.getClusterLeaves(clusterId, 200, 0, (err, leaves) => {
          if (err || !leaves || leaves.length === 0) return;
          const members = leaves
            .map((leaf) => leaf.properties)
            .filter(
              (properties): properties is MapEventResponse =>
                properties !== null &&
                typeof properties.id === 'string' &&
                typeof properties.ai_headline === 'string' &&
                typeof properties.category === 'string' &&
                typeof properties.category_color === 'string' &&
                typeof properties.importance_score === 'number' &&
                (properties.location_name === null ||
                  typeof properties.location_name === 'string') &&
                typeof properties.longitude === 'number' &&
                typeof properties.latitude === 'number',
            )
            .sort((left, right) => right.importance_score - left.importance_score);
          if (members.length === 0) return;

          if (members.length === 1) {
            const [member] = members;
            const lngLat: [number, number] = [
              member.longitude,
              member.latitude,
            ];
            setClusterEvents(null);
            setSelectedId(member.id, lngLat);
            map.current?.easeTo({
              center: lngLat,
              duration: 400,
              easing: (t) => t,
            });
            return;
          }

          setClusterEvents(members);
        });
      });

      map.current?.on('mouseenter', 'hermes-clusters', () => {
        if (map.current) map.current.getCanvas().style.cursor = 'pointer';
      });
      map.current?.on('mouseleave', 'hermes-clusters', () => {
        if (map.current) map.current.getCanvas().style.cursor = '';
      });

      updateBounds();
      const initialLinksVisible =
        useMapStore.getState().showRelationships &&
        !useMapStore.getState().isTlMode;
      const arcColorExpression: mapboxgl.ExpressionSpecification = [
        'match',
        ['get', 'relationship_type'],
        'CAUSED',
        RELATIONSHIP_COLORS.CAUSED,
        'FOLLOW_UP',
        RELATIONSHIP_COLORS.FOLLOW_UP,
        'REACTION',
        RELATIONSHIP_COLORS.REACTION,
        'RELATED',
        RELATIONSHIP_COLORS.RELATED,
        RELATIONSHIP_COLORS.RELATED,
      ];

      map.current?.addSource('relationship-edges-source', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });
      map.current?.addSource('relationship-partners-source', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });
      map.current?.addSource('actor-vectors-source', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });
      map.current?.addSource('actor-anchors-source', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });
      map.current?.addLayer({
        id: 'hermes-relationship-arcs-glow',
        type: 'line',
        source: 'relationship-edges-source',
        layout: {
          visibility: initialLinksVisible ? 'visible' : 'none',
          'line-cap': 'round',
          'line-join': 'round',
        },
        paint: {
          'line-color': arcColorExpression,
          'line-width': ['case', ['==', ['get', 'is_active'], true], 9.0, 5.0],
          'line-blur': ['case', ['==', ['get', 'is_active'], true], 5.0, 3.5],
          'line-opacity': ['case', ['==', ['get', 'is_active'], true], 0.48, 0.28],
          'line-emissive-strength': 1,
        },
      });
      map.current?.addLayer({
        id: 'hermes-relationship-arcs',
        type: 'line',
        source: 'relationship-edges-source',
        layout: {
          visibility: initialLinksVisible ? 'visible' : 'none',
          'line-cap': 'round',
          'line-join': 'round',
        },
        paint: {
          'line-color': arcColorExpression,
          'line-width': ['case', ['==', ['get', 'is_active'], true], 3.2, 2.0],
          'line-opacity': ['case', ['==', ['get', 'is_active'], true], 1.0, 0.72],
          'line-emissive-strength': 1,
        },
      });
      map.current?.addLayer({
        id: 'hermes-actor-vectors',
        type: 'line',
        source: 'actor-vectors-source',
        layout: {
          visibility: initialLinksVisible ? 'visible' : 'none',
          'line-cap': 'round',
          'line-join': 'round',
        },
        paint: {
          'line-color': ACTOR_VECTOR_COLOR,
          'line-dasharray': [2.2, 2.2],
          'line-width': ['case', ['==', ['get', 'is_active'], true], 2.4, 1.4],
          'line-opacity': ['case', ['==', ['get', 'is_active'], true], 0.95, 0.35],
          'line-emissive-strength': 1,
        },
      });
      map.current?.addSource('events-source', {
        type: 'geojson',
        data: events
          ? createGeoJson(events)
          : { type: 'FeatureCollection', features: [] },
        cluster: true,
        clusterMaxZoom: 18,
        clusterRadius: 50,
      });
      map.current?.addLayer({
        id: 'hermes-clusters',
        type: 'circle',
        source: 'events-source',
        filter: ['has', 'point_count'],
        paint: {
          'circle-color': [
            'step',
            ['zoom'],
            '#0b0d10',
            8,
            'rgba(0, 0, 0, 0)',
          ],
          'circle-radius': ['step', ['get', 'point_count'], 20, 10, 30, 50, 40],
          'circle-stroke-width': 1.5,
          'circle-stroke-color': '#00f0ff',
          'circle-stroke-opacity': 0.75,
          'circle-emissive-strength': 1,
        },
      });
      map.current?.addLayer({
        id: 'hermes-cluster-count',
        type: 'symbol',
        source: 'events-source',
        filter: ['has', 'point_count'],
        layout: {
          'text-field': '{point_count_abbreviated}',
          'text-font': ['JetBrains Mono Regular', 'Arial Unicode MS Bold'],
          'text-size': 12,
        },
        paint: {
          'text-color': '#00f0ff',
          'text-emissive-strength': 1,
        },
      });
      map.current?.addLayer({
        id: 'hermes-unclustered-point',
        type: 'circle',
        source: 'events-source',
        filter: ['!', ['has', 'point_count']],
        paint: {
          'circle-color': ['get', 'category_color'],
          'circle-radius': ['match', ['get', 'rank'], 1, 18, 2, 14, 3, 10, 6],
          'circle-stroke-width': [
            'case',
            ['>', ['coalesce', ['get', 'relationship_count'], 0], 0],
            2.2,
            1.5,
          ],
          'circle-stroke-color': [
            'case',
            ['>', ['coalesce', ['get', 'relationship_count'], 0], 0],
            '#00f0ff',
            '#f1ede2',
          ],
          'circle-stroke-opacity': [
            'case',
            ['>', ['coalesce', ['get', 'relationship_count'], 0], 0],
            0.85,
            0.45,
          ],
          'circle-emissive-strength': 1,
        },
      });
      map.current?.addSource('cited-events-source', {
        type: 'geojson',
        data: createCitedGeoJson([]),
      });
      map.current?.addLayer({
        id: 'hermes-cited-points',
        type: 'circle',
        source: 'cited-events-source',
        paint: {
          'circle-radius': 22,
          'circle-color': 'rgba(0, 0, 0, 0)',
          'circle-stroke-width': 3,
          'circle-stroke-color': '#00f0ff',
          'circle-stroke-opacity': 0.95,
        },
      });
      map.current?.addLayer({
        id: 'hermes-relationship-partners',
        type: 'circle',
        source: 'relationship-partners-source',
        layout: {
          visibility: initialLinksVisible ? 'visible' : 'none',
        },
        paint: {
          'circle-radius': 18,
          'circle-color': 'rgba(0, 0, 0, 0)',
          'circle-stroke-width': 2.5,
          'circle-stroke-color': '#ffb454',
          'circle-stroke-opacity': 0.95,
          'circle-emissive-strength': 1,
        },
      });
      map.current?.addLayer({
        id: 'hermes-actor-anchors',
        type: 'symbol',
        source: 'actor-anchors-source',
        layout: {
          visibility: initialLinksVisible ? 'visible' : 'none',
          'text-field': ['concat', '◇ ', ['get', 'name']],
          'text-font': ['JetBrains Mono Regular', 'Arial Unicode MS Bold'],
          'text-size': 10,
          'text-allow-overlap': true,
          'text-offset': [0, -1.1],
        },
        paint: {
          'text-color': ACTOR_VECTOR_COLOR,
          'text-halo-color': '#0b0d10',
          'text-halo-width': 1.5,
          'text-opacity': 0.95,
          'text-emissive-strength': 1,
        },
      });
    });

    map.current.on('moveend', updateBounds);
    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, [setViewport, setSelectedId, config.mapboxToken]);

  useEffect(() => {
    if (!map.current) return;

    const updateSource = () => {
      const source = map.current?.getSource(
        'events-source',
      ) as mapboxgl.GeoJSONSource;
      if (source && events) {
        const geojsonData = createGeoJson(events);
        source.setData(geojsonData);
      }
    };

    if (map.current.isStyleLoaded()) {
      updateSource();
    } else {
      map.current.once('load', updateSource);
      map.current.once('style.load', updateSource);
    }
  }, [events]);

  useEffect(() => {
    if (clusterEvents === null) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setClusterEvents(null);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [clusterEvents]);

  useEffect(() => {
    if (isTimelineMode) setClusterEvents(null);
  }, [isTimelineMode]);

  useEffect(() => {
    if (!map.current) return;

    const updateCitedSource = () => {
      const source = map.current?.getSource(
        'cited-events-source',
      ) as mapboxgl.GeoJSONSource | undefined;
      source?.setData(createCitedGeoJson(citedEvents));
    };

    if (map.current.isStyleLoaded()) {
      updateCitedSource();
    } else {
      map.current.once('load', updateCitedSource);
      map.current.once('style.load', updateCitedSource);
    }
  }, [citedEvents]);

  useEffect(() => {
    const mapInstance = map.current;
    if (!mapInstance) return;

    const updateRelationshipSources = () => {
      const geojson = buildRelationshipGeoJson(
        relationships ?? [],
        activeLinksEventId,
      );
      const actorGeojson = buildActorGeoJson(
        events ?? [],
        activeLinksEventId,
      );
      const edgesSource = mapInstance.getSource(
        'relationship-edges-source',
      ) as mapboxgl.GeoJSONSource | undefined;
      const partnersSource = mapInstance.getSource(
        'relationship-partners-source',
      ) as mapboxgl.GeoJSONSource | undefined;
      const actorVectorsSource = mapInstance.getSource(
        'actor-vectors-source',
      ) as mapboxgl.GeoJSONSource | undefined;
      const actorAnchorsSource = mapInstance.getSource(
        'actor-anchors-source',
      ) as mapboxgl.GeoJSONSource | undefined;

      edgesSource?.setData(geojson.edges);
      partnersSource?.setData(geojson.partners);
      actorVectorsSource?.setData(actorGeojson.vectors);
      actorAnchorsSource?.setData(actorGeojson.anchors);

      if (mapInstance.getLayer('hermes-relationship-arcs-glow')) {
        mapInstance.setPaintProperty(
          'hermes-relationship-arcs-glow',
          'line-opacity',
          [
            'case',
            ['==', ['get', 'is_active'], true],
            0.48,
            activeLinksEventId !== null ? 0.06 : 0.28,
          ],
        );
      }

      if (mapInstance.getLayer('hermes-relationship-arcs')) {
        mapInstance.setPaintProperty('hermes-relationship-arcs', 'line-opacity', [
          'case',
          ['==', ['get', 'is_active'], true],
          1.0,
          activeLinksEventId !== null ? 0.14 : 0.72,
        ]);
      }

      if (mapInstance.getLayer('hermes-actor-vectors')) {
        mapInstance.setPaintProperty('hermes-actor-vectors', 'line-opacity', [
          'case',
          ['==', ['get', 'is_active'], true],
          0.95,
          activeLinksEventId !== null ? 0.12 : 0.35,
        ]);
      }
    };

    if (mapInstance.getSource('relationship-edges-source')) {
      updateRelationshipSources();
    } else {
      mapInstance.once('load', updateRelationshipSources);
      mapInstance.once('style.load', updateRelationshipSources);
    }
  }, [relationships, events, activeLinksEventId]);

  useEffect(() => {
    const mapInstance = map.current;
    if (!mapInstance || focusRequest === null) return;

    const flyToCitation = () => {
      mapInstance.flyTo({
        center: focusRequest.lngLat,
        zoom: Math.max(mapInstance.getZoom(), 6),
        duration: 1200,
        essential: true,
      });
    };

    if (mapInstance.isStyleLoaded()) {
      flyToCitation();
    } else {
      mapInstance.once('load', flyToCitation);
    }
  }, [focusRequest]);

  // Toggle base layer visibility based on mode.
  // NOTE: We intentionally do NOT use map.isStyleLoaded() here. That returns false
  // whenever tiles are in flight (e.g. after panning), even though the style and
  // layers are fully registered. Since TlPanel only mounts after map.on('load'),
  // we know layers exist — guard with getLayer() in the loop instead.
  useEffect(() => {
    if (!map.current) return;
    const visibility = isTimelineMode ? 'none' : 'visible';
    const relationshipVisibility =
      !isTimelineMode && showRelationships ? 'visible' : 'none';

    [
      'hermes-clusters',
      'hermes-cluster-count',
      'hermes-unclustered-point',
      'hermes-cited-points',
    ].forEach((layer) => {
      if (map.current?.getLayer(layer)) {
        map.current.setLayoutProperty(layer, 'visibility', visibility);
      }
    });

    [
      'hermes-relationship-arcs-glow',
      'hermes-relationship-arcs',
      'hermes-relationship-partners',
      'hermes-actor-vectors',
      'hermes-actor-anchors',
    ].forEach(
      (layer) => {
        if (map.current?.getLayer(layer)) {
          map.current.setLayoutProperty(
            layer,
            'visibility',
            relationshipVisibility,
          );
        }
      },
    );
  }, [isTimelineMode, showRelationships]);

  return (
    <>
      <div ref={mapContainer} className="fixed inset-0 z-0 h-screen w-screen" />

      <CornerReticle
        className="inset-x-3 bottom-10 top-15 z-10 opacity-45"
        tone="bone"
        size="sm"
      />

      <MapHud events={events ?? []} isFetching={isFetching} />

      {isMapReady && !isTimelineMode && (
        <EventPopup
          map={map.current}
          onThreadOpen={onThreadChange}
          popupInsets={popupInsets}
        />
      )}
      {isMapReady && !isTimelineMode && clusterEvents !== null && (
        <ClusterList
          events={clusterEvents}
          hasRightPanel={threadId !== null}
          onClose={() => setClusterEvents(null)}
          onSelect={(event) => {
            const lngLat: [number, number] = [
              event.longitude,
              event.latitude,
            ];
            setClusterEvents(null);
            setSelectedId(event.id, lngLat);
            map.current?.easeTo({
              center: lngLat,
              duration: 400,
              easing: (t) => t,
            });
          }}
        />
      )}
      {isMapReady && !isTimelineMode && threadId !== null && (
        <StoryPanel
          map={map.current}
          threadId={threadId}
          onClose={() => onThreadChange?.(null)}
        />
      )}
      {isMapReady && isTimelineMode && <TlPanel map={map.current} />}

      {isFetching && !isTimelineMode && <EventsLoader />}
    </>
  );
}
