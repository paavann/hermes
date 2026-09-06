import { useEffect, useRef } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'

import { useMapStore } from '../store/store'
import { useMapDataSync } from '../hooks/datasync'



mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN





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

        map.current.on('load', updateBounds)
        map.current.on('moveend', updateBounds)
        return () => {
            map.current?.remove()
            map.current = null
        }
    }, [setViewport])

    
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