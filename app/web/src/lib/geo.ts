import type { MissionAreaSummary, ResolvedLocation } from "@/api/types";

export interface GeoPoint {
  latitude: number;
  longitude: number;
}

export interface GeoRectangle {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface MercatorPoint {
  x: number;
  y: number;
}

const TILE_SIZE = 256;

export function kilometersPerDegreeLat() {
  return 111.32;
}

export function kilometersPerDegreeLon(latitude: number) {
  return Math.max(111.32 * Math.cos((latitude * Math.PI) / 180), 0.1);
}

export function previewBounds(location: ResolvedLocation, missionArea?: MissionAreaSummary | null): GeoRectangle {
  const widthKm = Math.max(
    location.preview_span_km ?? 18,
    Number(missionArea?.width_km ?? 0) * 1.55,
    8,
  );
  const heightKm = Math.max(
    (location.preview_span_km ?? 18) * 0.72,
    Number(missionArea?.height_km ?? 0) * 1.55,
    6,
  );
  const latDelta = heightKm / kilometersPerDegreeLat();
  const lonDelta = widthKm / kilometersPerDegreeLon(location.latitude);
  return {
    north: location.latitude + latDelta / 2,
    south: location.latitude - latDelta / 2,
    east: location.longitude + lonDelta / 2,
    west: location.longitude - lonDelta / 2,
  };
}

export function latLonToCanvasPoint(point: GeoPoint, bounds: GeoRectangle, width: number, height: number) {
  const x = ((point.longitude - bounds.west) / Math.max(bounds.east - bounds.west, 1e-9)) * width;
  const y = ((bounds.north - point.latitude) / Math.max(bounds.north - bounds.south, 1e-9)) * height;
  return { x: clamp(x, 0, width), y: clamp(y, 0, height) };
}

export function canvasPointToLatLon(x: number, y: number, bounds: GeoRectangle, width: number, height: number): GeoPoint {
  const longitude = bounds.west + (clamp(x, 0, width) / Math.max(width, 1)) * (bounds.east - bounds.west);
  const latitude = bounds.north - (clamp(y, 0, height) / Math.max(height, 1)) * (bounds.north - bounds.south);
  return { latitude, longitude };
}

export function rectangleFromPoints(start: GeoPoint, end: GeoPoint): GeoRectangle {
  return {
    north: Math.max(start.latitude, end.latitude),
    south: Math.min(start.latitude, end.latitude),
    east: Math.max(start.longitude, end.longitude),
    west: Math.min(start.longitude, end.longitude),
  };
}

export function rectangleDimensionsKm(rectangle: GeoRectangle) {
  const midLat = (rectangle.north + rectangle.south) / 2;
  return {
    widthKm: Math.abs(rectangle.east - rectangle.west) * kilometersPerDegreeLon(midLat),
    heightKm: Math.abs(rectangle.north - rectangle.south) * kilometersPerDegreeLat(),
  };
}

export function formatCoordinate(point: GeoPoint | undefined | null) {
  if (!point) {
    return "Not set";
  }
  return `${point.latitude.toFixed(4)}, ${point.longitude.toFixed(4)}`;
}

export function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

export function zoomForKilometerSpan(latitude: number, spanKm: number, viewportWidth: number) {
  const metersPerPixel = Math.max((spanKm * 1000) / Math.max(viewportWidth, 1), 5);
  const zoom = Math.log2((156543.03392 * Math.cos((latitude * Math.PI) / 180)) / metersPerPixel);
  return clamp(Math.round(zoom), 6, 16);
}

export function latLonToWorldPixel(point: GeoPoint, zoom: number): MercatorPoint {
  const scale = TILE_SIZE * 2 ** zoom;
  const sinLat = Math.sin((point.latitude * Math.PI) / 180);
  return {
    x: ((point.longitude + 180) / 360) * scale,
    y: (0.5 - Math.log((1 + sinLat) / (1 - sinLat)) / (4 * Math.PI)) * scale,
  };
}

export function worldPixelToLatLon(point: MercatorPoint, zoom: number): GeoPoint {
  const scale = TILE_SIZE * 2 ** zoom;
  const longitude = (point.x / scale) * 360 - 180;
  const mercatorY = Math.PI * (1 - (2 * point.y) / scale);
  const latitude = (Math.atan(Math.sinh(mercatorY)) * 180) / Math.PI;
  return { latitude, longitude };
}

export function latLonToViewportPoint(
  point: GeoPoint,
  center: GeoPoint,
  zoom: number,
  width: number,
  height: number,
) {
  const world = latLonToWorldPixel(point, zoom);
  const centerWorld = latLonToWorldPixel(center, zoom);
  return {
    x: world.x - (centerWorld.x - width / 2),
    y: world.y - (centerWorld.y - height / 2),
  };
}

export function viewportPointToLatLon(
  x: number,
  y: number,
  center: GeoPoint,
  zoom: number,
  width: number,
  height: number,
) {
  const centerWorld = latLonToWorldPixel(center, zoom);
  return worldPixelToLatLon(
    {
      x: centerWorld.x - width / 2 + x,
      y: centerWorld.y - height / 2 + y,
    },
    zoom,
  );
}

export function normalizeTileX(tileX: number, zoom: number) {
  const limit = 2 ** zoom;
  return ((tileX % limit) + limit) % limit;
}

export function validTileY(tileY: number, zoom: number) {
  const limit = 2 ** zoom;
  return tileY >= 0 && tileY < limit;
}

export function tileUrl(template: string, zoom: number, tileX: number, tileY: number) {
  return template
    .replaceAll("{z}", String(zoom))
    .replaceAll("{x}", String(normalizeTileX(tileX, zoom)))
    .replaceAll("{y}", String(tileY));
}
