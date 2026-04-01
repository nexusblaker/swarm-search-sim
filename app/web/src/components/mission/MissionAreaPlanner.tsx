import { useMemo, useRef, useState, type PointerEvent } from "react";

import type { MissionAreaSummary, ResolvedLocation } from "@/api/types";
import {
  canvasPointToLatLon,
  clamp,
  formatCoordinate,
  latLonToCanvasPoint,
  previewBounds,
  rectangleDimensionsKm,
  rectangleFromPoints,
  type GeoPoint,
} from "@/lib/geo";

const VIEWBOX_WIDTH = 1000;
const VIEWBOX_HEIGHT = 620;

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

function stagingPoint(missionArea?: MissionAreaSummary | null): GeoPoint | null {
  const staging = missionArea?.staging;
  if (!staging) {
    return null;
  }
  if (typeof staging.latitude !== "number" || typeof staging.longitude !== "number") {
    return null;
  }
  return { latitude: staging.latitude, longitude: staging.longitude };
}

export function MissionAreaPlanner({
  location,
  missionArea,
  isUpdating,
  onRectangleChange,
  onStagingChange,
}: {
  location: ResolvedLocation | null;
  missionArea?: MissionAreaSummary | null;
  isUpdating?: boolean;
  onRectangleChange: (rectangle: { north: number; south: number; east: number; west: number }) => void;
  onStagingChange: (point: { latitude: number; longitude: number; label: string; placement: string }) => void;
}) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [dragCurrent, setDragCurrent] = useState<{ x: number; y: number } | null>(null);
  const [placingStaging, setPlacingStaging] = useState(false);

  const bounds = useMemo(() => (location ? previewBounds(location, missionArea) : null), [location, missionArea]);
  const resolvedRectangle = areaRectangle(missionArea);
  const resolvedStaging = stagingPoint(missionArea);
  const seed = useMemo(() => Math.abs(Math.round((location?.latitude ?? 0) * 1000 + (location?.longitude ?? 0) * 1000)), [location]);

  const dragRectangle = useMemo(() => {
    if (!bounds || !dragStart || !dragCurrent) {
      return null;
    }
    return rectangleFromPoints(
      canvasPointToLatLon(dragStart.x, dragStart.y, bounds, VIEWBOX_WIDTH, VIEWBOX_HEIGHT),
      canvasPointToLatLon(dragCurrent.x, dragCurrent.y, bounds, VIEWBOX_WIDTH, VIEWBOX_HEIGHT),
    );
  }, [bounds, dragCurrent, dragStart]);

  function pointerPosition(event: PointerEvent<SVGSVGElement>) {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) {
      return null;
    }
    const x = ((event.clientX - rect.left) / Math.max(rect.width, 1)) * VIEWBOX_WIDTH;
    const y = ((event.clientY - rect.top) / Math.max(rect.height, 1)) * VIEWBOX_HEIGHT;
    return { x: clamp(x, 0, VIEWBOX_WIDTH), y: clamp(y, 0, VIEWBOX_HEIGHT) };
  }

  function handlePointerDown(event: PointerEvent<SVGSVGElement>) {
    if (!bounds) {
      return;
    }
    const point = pointerPosition(event);
    if (!point) {
      return;
    }
    if (placingStaging) {
      const latLon = canvasPointToLatLon(point.x, point.y, bounds, VIEWBOX_WIDTH, VIEWBOX_HEIGHT);
      onStagingChange({ ...latLon, label: "Primary staging point", placement: "map" });
      setPlacingStaging(false);
      return;
    }
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
    if (!dragStart || !bounds) {
      return;
    }
    const point = pointerPosition(event) ?? dragCurrent ?? dragStart;
    const rectangle = rectangleFromPoints(
      canvasPointToLatLon(dragStart.x, dragStart.y, bounds, VIEWBOX_WIDTH, VIEWBOX_HEIGHT),
      canvasPointToLatLon(point.x, point.y, bounds, VIEWBOX_WIDTH, VIEWBOX_HEIGHT),
    );
    const dimensions = rectangleDimensionsKm(rectangle);
    if (dimensions.widthKm >= 1.0 && dimensions.heightKm >= 1.0) {
      onRectangleChange(rectangle);
    }
    setDragStart(null);
    setDragCurrent(null);
    svgRef.current?.releasePointerCapture(event.pointerId);
  }

  if (!location || !bounds) {
    return (
      <div className="rounded-[28px] border border-dashed border-border bg-surfaceAlt/35 p-6 text-sm leading-6 text-muted">
        Resolve a place name or coordinate pair to open the mission-area planner.
      </div>
    );
  }

  const displayedRectangle = dragRectangle ?? resolvedRectangle;
  const rectanglePoints = displayedRectangle
    ? {
        topLeft: latLonToCanvasPoint(
          { latitude: displayedRectangle.north, longitude: displayedRectangle.west },
          bounds,
          VIEWBOX_WIDTH,
          VIEWBOX_HEIGHT,
        ),
        bottomRight: latLonToCanvasPoint(
          { latitude: displayedRectangle.south, longitude: displayedRectangle.east },
          bounds,
          VIEWBOX_WIDTH,
          VIEWBOX_HEIGHT,
        ),
      }
    : null;
  const centerMarker = latLonToCanvasPoint(
    { latitude: location.latitude, longitude: location.longitude },
    bounds,
    VIEWBOX_WIDTH,
    VIEWBOX_HEIGHT,
  );
  const stagingMarker = resolvedStaging
    ? latLonToCanvasPoint(resolvedStaging, bounds, VIEWBOX_WIDTH, VIEWBOX_HEIGHT)
    : null;

  return (
    <div className="rounded-[28px] border border-border bg-[#08111b] p-4 shadow-soft">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="section-kicker">Mission area planner</p>
          <p className="mt-2 text-base font-semibold text-white">{location.display_name}</p>
          <p className="mt-1 text-sm leading-6 text-muted">
            Drag to reshape the AOI. Click staging mode, then click the map to place the base.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="pill">{missionArea?.shape_summary ?? "Rectangle AOI"}</span>
          <span className="pill">{missionArea?.grid_resolution_m ?? "500"} m cells</span>
          <button type="button" className={placingStaging ? "primary-button" : "secondary-button"} onClick={() => setPlacingStaging((current) => !current)}>
            {placingStaging ? "Click map to place base" : "Place staging point"}
          </button>
        </div>
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
        className="w-full rounded-[24px] border border-border/80 bg-[radial-gradient(circle_at_top,#0f2238,transparent_48%),linear-gradient(180deg,#08101a,#0b1624)]"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
      >
        <defs>
          <linearGradient id="aoi-fill" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(143,180,214,0.22)" />
            <stop offset="100%" stopColor="rgba(143,180,214,0.08)" />
          </linearGradient>
        </defs>
        <rect x="0" y="0" width={VIEWBOX_WIDTH} height={VIEWBOX_HEIGHT} fill="transparent" />
        {Array.from({ length: 9 }).map((_, index) => (
          <line
            key={`v-${index}`}
            x1={(VIEWBOX_WIDTH / 8) * index}
            y1="0"
            x2={(VIEWBOX_WIDTH / 8) * index}
            y2={VIEWBOX_HEIGHT}
            stroke="rgba(255,255,255,0.05)"
            strokeWidth="1"
          />
        ))}
        {Array.from({ length: 7 }).map((_, index) => (
          <line
            key={`h-${index}`}
            x1="0"
            y1={(VIEWBOX_HEIGHT / 6) * index}
            x2={VIEWBOX_WIDTH}
            y2={(VIEWBOX_HEIGHT / 6) * index}
            stroke="rgba(255,255,255,0.05)"
            strokeWidth="1"
          />
        ))}
        {Array.from({ length: 5 }).map((_, index) => (
          <path
            key={`contour-${index}`}
            d={contourPath(index, seed)}
            fill="none"
            stroke="rgba(173, 193, 214, 0.14)"
            strokeWidth="2"
          />
        ))}

        {rectanglePoints ? (
          <g>
            <rect
              x={Math.min(rectanglePoints.topLeft.x, rectanglePoints.bottomRight.x)}
              y={Math.min(rectanglePoints.topLeft.y, rectanglePoints.bottomRight.y)}
              width={Math.abs(rectanglePoints.bottomRight.x - rectanglePoints.topLeft.x)}
              height={Math.abs(rectanglePoints.bottomRight.y - rectanglePoints.topLeft.y)}
              fill="url(#aoi-fill)"
              stroke="rgba(143,180,214,0.92)"
              strokeWidth="4"
              rx="20"
            />
            <text
              x={Math.min(rectanglePoints.topLeft.x, rectanglePoints.bottomRight.x) + 16}
              y={Math.min(rectanglePoints.topLeft.y, rectanglePoints.bottomRight.y) + 28}
              fill="#dfe8f1"
              fontSize="18"
              fontWeight="600"
            >
              Search area
            </text>
          </g>
        ) : null}

        <g>
          <circle cx={centerMarker.x} cy={centerMarker.y} r="10" fill="#f8fafc" />
          <circle cx={centerMarker.x} cy={centerMarker.y} r="18" fill="none" stroke="rgba(248,250,252,0.4)" strokeWidth="2" />
          <text x={centerMarker.x + 18} y={centerMarker.y - 14} fill="#f8fafc" fontSize="16">
            Search centre
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
      </svg>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-[20px] border border-border/70 bg-surfaceAlt/45 px-4 py-3">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Area</p>
          <p className="mt-2 text-sm font-medium text-white">
            {missionArea?.area_sq_km ? `${missionArea.area_sq_km.toFixed(1)} km²` : "Draw an area"}
          </p>
        </div>
        <div className="rounded-[20px] border border-border/70 bg-surfaceAlt/45 px-4 py-3">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Staging point</p>
          <p className="mt-2 text-sm font-medium text-white">
            {formatCoordinate(resolvedStaging)}
          </p>
        </div>
        <div className="rounded-[20px] border border-border/70 bg-surfaceAlt/45 px-4 py-3">
          <p className="text-xs uppercase tracking-[0.14em] text-muted">Planner status</p>
          <p className="mt-2 text-sm font-medium text-white">
            {isUpdating ? "Refreshing area model..." : "Ready"}
          </p>
        </div>
      </div>
    </div>
  );
}
