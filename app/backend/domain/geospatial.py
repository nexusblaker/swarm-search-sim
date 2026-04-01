"""Local-first location resolution and AOI preview helpers."""

from __future__ import annotations

from typing import Any

from src.environment.mission_area import preview_mission_area, resolve_location_input


class GeospatialService:
    """Resolve mission locations and preview AOI-backed grid metadata."""

    def resolve_location(self, request: dict[str, Any]) -> dict[str, Any]:
        return resolve_location_input(
            query=request.get("query"),
            latitude=request.get("latitude"),
            longitude=request.get("longitude"),
        )

    def preview_area(self, request: dict[str, Any]) -> dict[str, Any]:
        location = dict(request.get("location") or {})
        mission_area = preview_mission_area(
            location=location,
            shape_type=str(request.get("shape_type", "rectangle")),
            rectangle=request.get("rectangle"),
            polygon=request.get("polygon"),
            grid_resolution_m=float(request.get("grid_resolution_m", 500.0)),
            staging=request.get("staging"),
            last_known_status=str(request.get("last_known_status", "unknown")),
            environment_type=str(request.get("environment_type", "mixed_terrain")),
            weather=str(request.get("weather", "clear")),
        )
        return {"mission_area": mission_area}
