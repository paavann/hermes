import { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css'; // Ensure CSS is imported for proper rendering

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN || '';

export function MapView() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);

  useEffect(() => {
    if (map.current || !mapContainer.current) return;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [0, 20],
      zoom: 1.5,
      projection: 'mercator', // Force 2D flat Mercator projection
      pitch: 0,               // Disable camera tilt
      maxPitch: 0,            // Prevent user from pitching into 3D view
      dragRotate: false,      // Optional: Prevent rotating/tilting with right-click drag
      touchPitch: false,      // Optional: Prevent two-finger tilt on touch devices
    });

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  return (
    <div 
      ref={mapContainer} 
      className="fixed inset-0 w-screen h-screen z-0" 
    />
  );
}