import { useEffect, useRef, useState } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { useMapStore } from '../store/store'
import { useMapDataSync } from '../hooks/datasync'
import { EventPopup } from './components/EventPopup'
import type { FeatureCollection } from 'geojson'
import type { MapEventResponse } from '@hermes/util-types'

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN



const createGeoJson = (events: MapEventResponse[]): FeatureCollection => {
    const uniqueEvents = new Map<string, MapEventResponse>();
    
    // Deduplicate by location to prevent concentric circles for the same event
    events.forEach(event => {
        // Use 4 decimal places (~11m precision) to group virtually identical locations
        const key = `${event.latitude.toFixed(4)},${event.longitude.toFixed(4)}`;
        if (!uniqueEvents.has(key)) {
            uniqueEvents.set(key, event);
        } else {
            // If they overlap, keep the one with the higher trending score
            const existing = uniqueEvents.get(key)!;
            if (event.trending_score > existing.trending_score) {
                uniqueEvents.set(key, event);
            }
        }
    });

    return {
        type: 'FeatureCollection',
        features: Array.from(uniqueEvents.values()).map((event, index) => ({
            type: 'Feature',
            geometry: {
                type: 'Point',
                coordinates: [event.longitude, event.latitude],
            },
            properties: {
                ...event,
                rank: index + 1
            },
        }))
    }
}





export function MapView() {
    const mapContainer = useRef<HTMLDivElement>(null)
    const map = useRef<mapboxgl.Map | null>(null)
    const [isMapReady, setIsMapReady] = useState(false)
    const setViewport = useMapStore((state) => state.setViewport)
    const { data: events, isFetching, } = useMapDataSync()
    const setSelectedId = useMapStore((s) => s.setSelectedEventId)

    useEffect(() => {
        if(!mapContainer.current || map.current) return

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
        })

        const updateBounds = () => {
            if(!map.current) return
            const bounds = map.current.getBounds()
            if(bounds) {
                setViewport({
                    north: bounds.getNorthEast().lat,
                    south: bounds.getSouthWest().lat,
                    east: bounds.getNorthEast().lng,
                    west: bounds.getSouthWest().lng,
                })
            }
        }

        map.current.on('load', () => {
            setIsMapReady(true)
            
            map.current?.on('click', 'hermes-unclustered-point', (e) => {
                if(e.features && e.features[0] && map.current) {
                    const eventId = e.features[0].properties?.id
                    if(eventId) {
                        const lngLat: [number, number] = [e.lngLat.lng, e.lngLat.lat]
                        setSelectedId(eventId, lngLat)
                        
                        // Automatically pan the camera so the popup is perfectly centered
                        map.current.easeTo({
                            center: lngLat,
                            duration: 800,
                            easing: (t) => t * (2 - t) // smooth ease out
                        })
                    }
                }
            })
            map.current?.on('mouseenter', 'hermes-unclustered-point', () => {
                if (map.current) map.current.getCanvas().style.cursor = 'pointer'
            })
            map.current?.on('mouseleave', 'hermes-unclustered-point', () => {
                if(map.current) map.current.getCanvas().style.cursor = ''
            })

            // Cluster robotic zoom interaction
            map.current?.on('click', 'hermes-clusters', (e) => {
                const features = map.current?.queryRenderedFeatures(e.point, { layers: ['hermes-clusters'] });
                if (!features || !features[0]) return;
                
                const clusterId = features[0].properties?.cluster_id;
                const source = map.current?.getSource('events-source') as mapboxgl.GeoJSONSource;
                
                source.getClusterExpansionZoom(clusterId, (err, zoom) => {
                    if (err || !map.current) return;
                    
                    const geometry = features[0].geometry;
                    if (geometry.type === 'Point') {
                        map.current.easeTo({
                            center: geometry.coordinates as [number, number],
                            zoom: zoom,
                            duration: 400,
                            easing: (t) => t // Pure linear easing for robotic feel
                        });
                    }
                });
            });
            
            map.current?.on('mouseenter', 'hermes-clusters', () => {
                if (map.current) map.current.getCanvas().style.cursor = 'pointer'
            })
            map.current?.on('mouseleave', 'hermes-clusters', () => {
                if(map.current) map.current.getCanvas().style.cursor = ''
            })

            updateBounds()
            map.current?.addSource('events-source', {
                type: 'geojson',
                data: { type: 'FeatureCollection', features: [], },
                cluster: true,
                clusterMaxZoom: 14,
                clusterRadius: 50,
            })
            map.current?.addLayer({
                id: 'hermes-clusters',
                type: 'circle',
                source: 'events-source',
                filter: ['has', 'point_count'],
                paint: {
                    'circle-color': [
                        'step',
                        ['zoom'],
                        '#808080', // Pure grey instead of slate navy
                        8, // At zoom level 8...
                        'rgba(0, 0, 0, 0)' // Become transparent (hollow outline)
                    ],
                    'circle-radius': [
                        'step',
                        ['get', 'point_count'],
                        20,
                        10,
                        30,
                        50,
                        40,                     
                    ],
                    'circle-stroke-width': 2,
                    'circle-stroke-color': "#94a3b8",
                    'circle-emissive-strength': 1,
                }
            })
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
                    'text-color': '#ffffff',
                    'text-emissive-strength': 1,
                }
            })
            map.current?.addLayer({
                id: 'hermes-unclustered-point',
                type: 'circle',
                source: 'events-source',
                filter: ['!', ['has', 'point_count']],
                paint: {
                    'circle-color': ['get', 'category_color'],
                    'circle-radius': [
                        'match',
                        ['get', 'rank'],
                        1, 18,
                        2, 14,
                        3, 10,
                        6
                    ],
                    'circle-stroke-width': 1,
                    'circle-stroke-color': "#000000",
                    'circle-emissive-strength': 1,
                }
            })            
        })

        map.current.on('moveend', updateBounds)
        return () => {
            map.current?.remove()
            map.current = null
        }
    }, [setViewport, setSelectedId])

    useEffect(() => {
        if(!map.current || !map.current.isStyleLoaded()) return
        const source = map.current.getSource('events-source') as mapboxgl.GeoJSONSource
        if(source && events) {
            const geojsonData = createGeoJson(events)
            source.setData(geojsonData)
        }
    }, [events])

    
    return (
        <>
            <div
                ref={mapContainer}
                className='fixed inset-0 w-screen h-screen z-0'
            />
            {isMapReady && <EventPopup map={map.current} />}
            {isFetching && (
                <div
                    className='fixed top-4 right-4 bg-hud-bg border border-hud-border text-neon-blue px-4 py-1.5 text-xs font-mono tracking-[0.15em] z-10 backdrop-blur-md uppercase shadow-[0_0_15px_rgba(59,130,246,0.3)] animate-pulse'
                >
                    SCANNING...
                </div>
            )}
        </>
    )
}