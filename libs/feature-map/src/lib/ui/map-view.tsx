import { useEffect, useRef } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { useMapStore } from '../store/store'
import { useMapDataSync } from '../hooks/datasync'
import type { FeatureCollection } from 'geojson'
import type { MapEventResponse } from '@hermes/util-types'

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN



const createGeoJson = (events: MapEventResponse[]): FeatureCollection => {
    return {
        type: 'FeatureCollection',
        features: events.map((event, index) => ({
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
    const setViewport = useMapStore((state) => state.setViewport)
    const { data: events, isFetching, } = useMapDataSync()

    useEffect(() => {
        if(!mapContainer.current || map.current) return

        map.current = new mapboxgl.Map({
            container: mapContainer.current,
            style: 'mapbox://styles/mapbox/dark-v11',
            center: [0, 20],
            zoom: 1.5,
            projection: 'mercator',
            pitch: 0,
            maxPitch: 0,
            dragRotate: false,
            touchPitch: false,
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
            updateBounds()
            map.current?.addSource('events-source', {
                type: 'geojson',
                data: { type: 'FeatureCollection', features: [], },
                cluster: true,
                clusterMaxZoom: 14,
                clusterRadius: 50,
            })
            map.current?.addLayer({
                id: 'clusters',
                type: 'circle',
                source: 'events-source',
                filter: ['has', 'point_count'],
                paint: {
                    'circle-color': "#475569",
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
                }
            })
            map.current?.addLayer({
                id: 'cluster-count',
                type: 'symbol',
                source: 'events-source',
                filter: ['has', 'point_count'],
                layout: {
                    'text-field': '{point_count_abbreviated}',
                    'text-font': ['Arial Unicode MS Bold'],
                    'text-size': 12,
                },
                paint: {
                    'text-color': '#ffffff',
                }
            })
            map.current?.addLayer({
                id: 'unclustered-point',
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
                }
            })
        })
        map.current.on('moveend', updateBounds)
        return () => {
            map.current?.remove()
            map.current = null
        }
    }, [setViewport])

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
            {isFetching && (
                <div
                    className='fixed top-4 right-4 bg-hud-bg border border-hud-border text-hud-glow px-4 py-2 text-sm font-mono z-10 backdrop-blur-md uppercase shadow-lg shadow-blue-900/20'
                >
                    Scanning region...
                </div>
            )}
        </>
    )
}