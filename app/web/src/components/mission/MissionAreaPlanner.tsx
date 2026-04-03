import { useEffect, useMemo, useRef, useState, type PointerEvent } from "react";

import type { MissionAreaSummary, ResolvedLocation } from "@/api/types";
import {
  clamp,
  formatCoordinate,
  latLonToViewportPoint,
  latLonToWorldPixel,
  normalizeTileX,
  rectangleDimensionsKm,
  rectangleFromPoints,
  tileUrl,
  validTileY,
  viewportPointToLatLon,
  zoomForKilometerSpan,
  type GeoPoint,
} from "@/lib/geo";

const VIEWBOX_WIDTH = 1000;
const VIEWBOX_HEIGHT = 620;
const TILE_SIZE = 256;
const HANDLE_HIT_RADIUS = 24;
const BASEMAP_TILE_URL = import.meta.env.VITE_BASEMAP_TILE_URL ?? "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const BASEMAP_STYLE_LABEL = import.meta.env.VITE_BASEMAP_STYLE_LABEL ?? "Live basemap";
const BASEMAP_ATTRIBUTION =
  import.meta.env.VITE_BASEMAP_ATTRIBUTION ?? "Map data © OpenStreetMap contributors";

type ResizeHandle = "nw" | "ne" | "se" | "sw";
type InteractionMode = "draw" | "placeStaging" | "placeLastKnown";

function contourPath(index: number, seed: number) {
  const points: string[] = [];
  const amplitude = 22 + index * 10;
  const vertical = 70 + index * 95;
  const phase = seed * 0.17 + index * 0.8;
  for (let x = 0; x <= VIEWBOX_WIDTH; x += 40) {
    const y =
      vertical +
      Math.sin(x / 115 + phase) * amplitude +
      Math.cos(x / 210 + phase * 0.6) * amplitude * 0.45;
    points.push(`${x},${clamp(y, 18, VIEWBOX_HEIGHT - 18)}`);
  }
  return `M ${points.join(" L ")}`;
}

function areaRectangle(missionArea?: MissionAreaSummary | null) {
  const rect = missionArea?.rectangle;
  if (!rect) {
    return null;
  }
  const north = Number(rect.north);
  const south = Number(rect.south);
  const east = Number(rect.east);
  const west = Number(rect.west);
  if (![north, south, east, west].every((value) => Number.isFinite(value))) {
    return null;
  }
  return { north, south, east, west };
}

function pointFromRecord(
  value:
    | MissionAreaSummary["staging"]
    | MissionAreaSummary["last_known_location"]
    | MissionAreaSummary["center"]
    | ResolvedLocation
    | null
    | undefined,
): GeoPoint | null {
  if (!value || typeof value.latitude !== "number" || typeof value.longitude !== "number") {
    return null;
  }
  return { latitude: value.latitude, longitude: value.longitude };
}

function resizeHandles(rectanglePoints: {
  topLeft: { x: number; y: number };
  topRight: { x: number; y: number };
  bottomRight: { x: number; y: number };
  bottomLeft: { x: number; y: number };
}) {
  return {
    nw: rectanglePoints.topLeft,
    ne: rectanglePoints.topRight,
    se: rectanglePoints.bottomRight,
    sw: rectanglePoints.bottomLeft,
  } as const;
}

export function MissionAreaPlanner({
  location,
  missionArea,
  isUpdating,
  showLastKnownPlacement = false,
  onRectangleChange,
  onStagingChange,
  onLastKnownChange,
}: {
  location: ResolvedLocation | null;
  missionArea?: MissionAreaSummary | null;
  isUpdating?: boolean;
  showLastKnownPlacement?: boolean;
  onRectangleChange: (rectangle: { north: number; south: number; east: number; west: number }) => void;
  onStagingChange: (point: { latitude: number; longitude: number; label: string; placement: string }) => void;
  onLastKnownChange?: (point: { latitude: number; longitude: number; label: string; placement: string }) => void;
}) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [zoom, setZoom] = useState(11);
  const [tileErrors, setTileErrors] = useState(0);
  const [interactionMode, setInteractionMode] = useState<InteractionMode>("draw");
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [dragCurrent, setDragCurrent] = useState<{ x: number; y: number } | null>(null);
  const [resizeHandle, setResizeHandle] = useState<ResizeHandle | null>(null);

  const mapCenter =
    pointFromRecord(missionArea?.center) ??
    (location ? { latitude: location.latitude, longitude: location.longitude } : null);
  const resolvedRectangle = areaRectangle(missionArea);
  const resolvedStaging = pointFromRecord(missionArea?.staging);
  const lastKnownPoint = pointFromRecord(missionArea?.last_known_location);
  const seed = useMemo(
    () => Math.abs(Math.round((location?.latitude ?? 0) * 1000 + (location?.longitude ?? 0) * 1000)),
    [location],
  );

  useEffect(() => {
    if (!location) {
      return;
    }
    const spanKm = Math.max(location.preview_span_km ?? 18, Number(missionArea?.width_km ?? 0) * 1.3, 8);
    setZoom(zoomForKilometerSpan(location.latitude, spanKm, VIEWBOX_WIDTH));
    setTileErrors(0);
  }, [location?.display_name, location?.latitude, missionArea?.width_km]);

  const tileDescriptors = useMemo(() => {
    if (!mapCenter) {
      return [];
    }
    const centerWorld = latLonToWorldPixel(mapCenter, zoom);
    const left = centerWorld.x - VIEWBOX_WIDTH / 2;
    const top = centerWorld.y - VIEWBOX_HEIGHT / 2;
    const startTileX = Math.floor(left / TILE_SIZE);
    const endTileX = Math.floor((left + VIEWBOX_WIDTH) / TILE_SIZE);
    const startTileY = Math.floor(top / TILE_SIZE);
    const endTileY = Math.floor((top + VIEWBOX_HEIGHT) / TILE_SIZE);
    const items: Array<{ id: string; href: string; x: number; y: number }> = [];
    for (let tileX = startTileX; tileX <= endTileX; tileX += 1) {
      for (let tileY = startTileY; tileY <= endTileY; tileY += 1) {
        if (!validTileY(tileY, zoom)) {
          continue;
        }
        items.push({
          id: `${zoom}-${tileX}-${tileY}`,
          href: tileUrl(BASEMAP_TILE_URL, zoom, tileX, tileY),
          x: tileX * TILE_SIZE - left,
          y: tileY * TILE_SIZE - top,
        });
      }
    }
    return items;
  }, [mapCenter, zoom]);

  function pointerPosition(event: PointerEvent<SVGSVGElement>) {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) {
      return null;
    }
    const x = ((event.clientX - rect.left) / Math.max(rect.width, 1)) * VIEWBOX_WIDTH;
    const y = ((event.clientY - rect.top) / Math.max(rect.height, 1)) * VIEWBOX_HEIGHT;
    return { x: clamp(x, 0, VIEWBOX_WIDTH), y: clamp(y, 0, VIEWBOX_HEIGHT) };
  }

  const previewRectangle = useMemo(() => {
    if (!mapCenter || !dragStart || !dragCurrent) {
      return null;
    }
    if (resizeHandle && resolvedRectangle) {
      const currentLatLon = viewportPointToLatLon(
        dragCurrent.x,
        dragCurrent.y,
        mapCenter,
        zoom,
        VIEWBOX_WIDTH,
        VIEWBOX_HEIGHT,
      );
      const opposite =
        resizeHandle === "nw"
          ? { latitude: resolvedRectangle.south, longitude: resolvedRectangle.east }
          : resizeHandle === "ne"
            ? { latitude: resolvedRectangle.south, longitude: resolvedRectangle.west }
            : resizeHandle === "se"
              ? { latitude: resolvedRectangle.north, longitude: resolvedRectangle.west }
              : { latitude: resolvedRectangle.north, longitude: resolvedRectangle.east };
      return rectangleFromPoints(currentLatLon, opposite);
    }
    return rectangleFromPoints(
      viewportPointToLatLon(dragStart.x, dragStart.y, mapCenter, zoom, VIEWBOX_WIDTH, VIEWBOX_HEIGHT),
      viewportPointToLatLon(dragCurrent.x, dragCurrent.y, mapCenter, zoom, VIEWBOX_WIDTH, VIEWBOX_HEIGHT),
    );
  }, [dragCurrent, dragStart, mapCenter, resizeHandle, resolvedRectangle, zoom]);

  const displayedRectangle = previewRectangle ?? resolvedRectangle;
  const rectanglePoints = displayedRectangle && mapCenter
    ? {
        topLeft: latLonToViewportPoint(
          { latitude: displayedRectangle.north, longitude: displayedRectangle.west },
          mapCenter,
          zoom,
          VIEWBOX_WIDTH,
          VIEWBOX_HEIGHT,
        ),
        topRight: latLonToViewportPoint(
          { latitude: displayedRectangle.north, longitude: displayedRectangle.east },
          mapCenter,
          zoom,
          VIEWBOX_WIDTH,
          VIEWBOX_HEIGHT,
        ),
        bottomRight: latLonToViewportPoint(
          { latitude: displayedRectangle.south, longitude: displayedRectangle.east },
          mapCenter,
          zoom,
          VIEWBOX_WIDTH,
          VIEWBOX_HEIGHT,
        ),
        bottomLeft: latLonToViewportPoint(
          { latitude: displayedRectangle.south, longitude: displayedRectangle.west },
          mapCenter,
          zoom,
          VIEWBOX_WIDTH,
          VIEWBOX_HEIGHT,
        ),
      }
    : null;

  const handleMap = rectanglePoints ? resizeHandles(rectanglePoints) : null;

  function detectHandle(point: { x: number; y: number }): ResizeHandle | null {
    if (!handleMap) {
      return null;
    }
    const entries = Object.entries(handleMap) as Array<[ResizeHandle, { x: number; y: number }]>;
    for (const [key, value] of entries) {
      const distance = Math.hypot(value.x - point.x, value.y - point.y);
      if (distance <= HANDLE_HIT_RADIUS) {
        return key;
      }
    }
    return null;
  }

  function handlePointerDown(event: PointerEvent<SVGSVGElement>) {
    if (!mapCenter) {
      return;
    }
    const point = pointerPosition(event);
    if (!point) {
      return;
    }
    if (interactionMode === "placeStaging") {
      const latLon = viewportPointToLatLon(point.x, point.y, mapCenter, zoom, VIEWBOX_WIDTH, VIEWBOX_HEIGHT);
      onStagingChange({ ...latLon, label: "Primary staging point", placement: "map" });
      setInteractionMode("draw");
      return;
    }
    if (interactionMode === "placeLastKnown" && onLastKnownChange) {
      const latLon = viewportPointToLatLon(point.x, point.y, mapCenter, zoom, VIEWBOX_WIDTH, VIEWBOX_HEIGHT);
      onLastKnownChange({ ...latLon, label: "Last known location", placement: "map" });
      setInteractionMode("draw");
      return;
    }
    const handle = detectHandle(point);
    setResizeHandle(handle);
    setDragStart(point);
    setDragCurrent(point);
    svgRef.current?.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: PointerEvent<SVGSVGElement>) {
    if (!dragStart) {
      return;
    }
    const point = pointerPosition(event);
    if (!point) {
      return;
    }
    setDragCurrent(point);
  }

  function handlePointerUp(event: PointerEvent<SVGSVGElement>) {
    if (!dragStart) {
      return;
    }
    const rectangle = previewRectangle;
    if (rectangle) {
      const dimensions = rectangleDimensionsKm(rectangle);
      if (dimensions.widthKm >= 1.0 && dimensions.heightKm >= 1.0) {
        onRectangleChange(rectangle);
      }
    }
    setDragStart(null);
    setDragCurrent(null);
    setResizeHandle(null);
    svgRef.current?.releasePointerCapture(event.pointerId);
  }

  if (!location || !mapCenter) {
    return (
      <div className="rounded-[28px] border border-dashed border-border bg-surfaceAlt/35 p-6 text-sm leading-6 text-muted">
        Resolve a place name or coordinate pair to open the mission-area planner.
      </div>
    );
  }

  const centerMarker = latLonToViewportPoint(mapCenter, mapCenter, zoom, VIEWBOX_WIDTH, VIEWBOX_HEIGHT);
  const stagingMarker = resolvedStaging
    ? latLonToViewportPoint(resolvedStaging, mapCenter, zoom, VIEWBOX_WIDTH, VIEWBOX_HEIGHT)
    : null;
  const lastKnownMarker = lastKnownPoint
    ? latLonToViewportPoint(lastKnownPoint, mapCenter, zoom, VIEWBOX_WIDTH, VIEWBOX_HEIGHT)
    : null;
  const basemapUnavailable = tileErrors >= 4;
  const weatherSummary = missionArea?.weather_summary;
  const plannerStatusSummary = missionArea?.planner_status_summary;

  return (
    <div className="rounded-[28px] border border-border bg-[#08111b] p-4 shadow-soft">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="section-kicker">Mission area planner</p>
          <p className="mt-2 text-base font-semibold text-white">{location.display_name}</p>
          <p className="mt-1 text-sm leading-6 text-muted">
            {interactionMode === "placeStaging"
              ? "Click the map to place the staging/base point."
              : interactionMode === "placeLastKnown"
                ? "Click the map to place the last known location."
                : "Drag to draw or redraw the search box. Drag a corner handle to resize it."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="pill">{BASEMAP_STYLE_LABEL}</span>
          <span className="pill">{missionArea?.shape_summary ?? "Rectangle AOI"}</span>
          <button type="button" className={interactionMode === "draw" ? "primary-button" : "secondary-button"} onClick={() => setInteractionMode("draw")}>
            Draw area
          </button>
          <button
            type="button"
            className={interactionMode === "placeStaging" ? "primary-button" : "secondary-button"}
            onClick={() => setInteractionMode("placeStaging")}
          >
            Place base
          </button>
          {showLastKnownPlacement ? (
            <button
              type="button"
              className={interactionMode === "placeLastKnown" ? "primary-button" : "secondary-button"}
              onClick={() => setInteractionMode("placeLastKnown")}
            >
              Place last known
            </button>
          ) : null}
          <button type="button" className="secondary-button px-3" onClick={() => setZoom((current) => clamp(current - 1, 6, 16))}>
            -
          </button>
          <button type="button" className="secondary-button px-3" onClick={() => setZoom((current) => clamp(current + 1, 6, 16))}>
            +
          </button>
        </div>
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
        className="w-full rounded-[24px] border border-border/80 bg-[linear-gradient(180deg,#08101a,#0b1624)]"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
      >
        <rect x="0" y="0" width={VIEWBOX_WIDTH} height={VIEWBOX_HEIGHT} fill="#08111b" />
        {!basemapUnavailable
          ? tileDescriptors.map((tile) => (
              <image
                key={tile.id}
                href={tile.href}
                x={tile.x}
                y={tile.y}
                width={TILE_SIZE}
                height={TILE_SIZE}
                preserveAspectRatio="none"
                onError={() => setTileErrors((current) => current + 1)}
              />
            ))
          : null}
        <rect x="0" y="0" width={VIEWBOX_WIDTH} height={VIEWBOX_HEIGHT} fill="rgba(4, 9, 16, 0.24)" />
        {basemapUnavailable
          ? Array.from({ length: 5 }).map((_, index) => (
              <path
                key={`contour-${index}`}
                d={contourPath(index, seed)}
                fill="none"
                stroke="rgba(173, 193, 214, 0.14)"
                strokeWidth="2"
              />
            ))
          : null}

        {rectanglePoints ? (
          <g>
            <rect
              x={Math.min(rectanglePoints.topLeft.x, rectanglePoints.bottomRight.x)}
              y={Math.min(rectanglePoints.topLeft.y, rectanglePoints.bottomRight.y)}
              width={Math.abs(rectanglePoints.bottomRight.x - rectanglePoints.topLeft.x)}
              height={Math.abs(rectanglePoints.bottomRight.y - rectanglePoints.topLeft.y)}
              fill="rgba(143,180,214,0.14)"
              stroke="rgba(143,180,214,0.98)"
              strokeWidth="4"
              rx="18"
            />
            {(Object.values(handleMap ?? {}) as Array<{ x: number; y: number }>).map((point, index) => (
              <circle
                key={`handle-${index}`}
                cx={point.x}
                cy={point.y}
                r="10"
                fill="#dce8f4"
                stroke="rgba(8,17,27,0.95)"
                strokeWidth="3"
              />
            ))}
          </g>
        ) : null}

        <g>
          <circle cx={centerMarker.x} cy={centerMarker.y} r="9" fill="#f8fafc" />
          <circle cx={centerMarker.x} cy={centerMarker.y} r="18" fill="none" stroke="rgba(248,250,252,0.35)" strokeWidth="2" />
          <text x={centerMarker.x + 18} y={centerMarker.y - 14} fill="#f8fafc" fontSize="16">
            Map center
          </text>
        </g>

        {stagingMarker ? (
          <g>
            <rect x={stagingMarker.x - 11} y={stagingMarker.y - 11} width="22" height="22" rx="6" fill="#34d399" />
            <text x={stagingMarker.x + 18} y={stagingMarker.y + 6} fill="#d9fff0" fontSize="16">
              Base
            </text>
          </g>
        ) : null}

        {lastKnownMarker ? (
          <g>
            <circle cx={lastKnownMarker.x} cy={lastKnownMarker.y} r="11" fill="#f59e0b" />
            <circle cx={lastKnownMarker.x} cy={lastKnownMarker.y} r="24" fill="none" stroke="rgba(245,158,11,0.45)" strokeWidth="3" />
            <text x={lastKnownMarker.x + 18} y={lastKnownMarker.y + 6} fill="#ffe8c2" fontSize="16">
              Last known
            </text>
          </g>
        ) : null}
      </svg>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <div className="rounded-[20px] border border-border/70 bg-surfaceAlt/45 px-4 py-3">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Area</p>
          <p className="mt-2 text-sm font-medium text-white">
            {missionArea?.area_sq_km ? `${missionArea.area_sq_km.toFixed(1)} km²` : "Draw an area"}
          </p>
        </div>
        <div className="rounded-[20px] border border-border/70 bg-surfaceAlt/45 px-4 py-3">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Base</p>
          <p className="mt-2 text-sm font-medium text-white">{formatCoordinate(resolvedStaging)}</p>
        </div>
        <div className="rounded-[20px] border border-border/70 bg-surfaceAlt/45 px-4 py-3">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Last known</p>
          <p className="mt-2 text-sm font-medium text-white">
            {showLastKnownPlacement ? formatCoordinate(lastKnownPoint) : "Not required"}
          </p>
        </div>
        <div className="rounded-[20px] border border-border/70 bg-surfaceAlt/45 px-4 py-3">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Weather</p>
          <p className="mt-2 text-sm font-medium text-white">
            {weatherSummary?.condition_label ?? (isUpdating ? "Refreshing..." : "Pending")}
          </p>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs leading-6 text-muted">
        <p>{basemapUnavailable ? "Live basemap unavailable. Local fallback surface remains active." : BASEMAP_ATTRIBUTION}</p>
        <p>{plannerStatusSummary ?? weatherSummary?.fallback_note ?? missionArea?.last_known_summary ?? "Map-centered setup ready."}</p>
      </div>
    </div>
  );
}
