import { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useMapStore } from '../store/store';
import { useMapDataSync } from '../hooks/datasync';
import { CornerReticle } from '@hermes/ui-components';

import { ClusterList } from './components/ClusterList';
import { EventPopup } from './components/EventPopup';
import type { PopupInsets } from './components/EventPopup';
import { StoryPanel } from './components/StoryPanel';
import { TlPanel } from './components/TlPanel';
import { EventsLoader } from './components/EventsLoader';
import { MapHud } from './components/MapHud';
import { createCitedGeoJson } from './cited-geojson';
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
  const [clusterEvents, setClusterEvents] = useState<MapEventResponse[] | null>(
    null,
  );
  const setViewport = useMapStore((state) => state.setViewport);
  const { data: events, isFetching } = useMapDataSync();
  const setSelectedId = useMapStore((s) => s.setSelectedEventId);

  const isTimelineMode = useMapStore((s) => s.isTlMode);
  const citedEvents = useMapStore((s) => s.citedEvents);
  const focusRequest = useMapStore((s) => s.focusRequest);

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
      map.current?.on('mouseenter', 'hermes-unclustered-point', () => {
        if (map.current) map.current.getCanvas().style.cursor = 'pointer';
      });
      map.current?.on('mouseleave', 'hermes-unclustered-point', () => {
        if (map.current) map.current.getCanvas().style.cursor = '';
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
          'circle-stroke-width': 1.5,
          'circle-stroke-color': '#f1ede2',
          'circle-stroke-opacity': 0.45,
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
  }, [isTimelineMode]);

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
