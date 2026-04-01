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
