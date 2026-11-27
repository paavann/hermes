import type { BoundingBox } from '../store/store';

export function clampBoundingBox(viewport: BoundingBox): BoundingBox {
  return {
    north: Math.min(Math.max(viewport.north, -90), 90),
    south: Math.min(Math.max(viewport.south, -90), 90),
    east: Math.min(Math.max(viewport.east, -180), 180),
    west: Math.min(Math.max(viewport.west, -180), 180),
  };
}
