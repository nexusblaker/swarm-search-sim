"""Local-first mission-area resolution and deterministic AOI rasterisation."""

from __future__ import annotations

from math import cos, pi, radians, sqrt
import re
from typing import Any

import numpy as np

from src.environment.grid import GridEnvironment, TerrainType


MAX_SAFE_CELLS = 4_900
MIN_GRID_WIDTH = 12
MIN_GRID_HEIGHT = 10

LOCAL_GAZETTEER: list[dict[str, Any]] = [
    {
        "display_name": "Sydney, NSW",
        "latitude": -33.8688,
        "longitude": 151.2093,
        "aliases": ["sydney", "sydney nsw"],
        "terrain_hint": "urban",
        "preview_span_km": 26.0,
    },
    {
        "display_name": "Katoomba, NSW",
        "latitude": -33.7126,
        "longitude": 150.3119,
        "aliases": ["katoomba", "blue mountains", "blue mountains nsw"],
        "terrain_hint": "mountain",
        "preview_span_km": 20.0,
    },
    {
        "display_name": "Canberra, ACT",
        "latitude": -35.2809,
        "longitude": 149.13,
        "aliases": ["canberra", "act"],
        "terrain_hint": "mixed",
        "preview_span_km": 22.0,
    },
    {
        "display_name": "Melbourne, VIC",
        "latitude": -37.8136,
        "longitude": 144.9631,
        "aliases": ["melbourne", "melbourne vic"],
        "terrain_hint": "urban",
        "preview_span_km": 26.0,
    },
    {
        "display_name": "Brisbane, QLD",
        "latitude": -27.4698,
        "longitude": 153.0251,
        "aliases": ["brisbane", "brisbane qld"],
        "terrain_hint": "coastal",
        "preview_span_km": 24.0,
    },
    {
        "display_name": "Perth, WA",
        "latitude": -31.9523,
        "longitude": 115.8613,
        "aliases": ["perth", "perth wa"],
        "terrain_hint": "coastal",
        "preview_span_km": 24.0,
    },
    {
        "display_name": "Adelaide, SA",
        "latitude": -34.9285,
        "longitude": 138.6007,
        "aliases": ["adelaide", "adelaide sa"],
        "terrain_hint": "mixed",
        "preview_span_km": 22.0,
    },
    {
        "display_name": "Hobart, TAS",
        "latitude": -42.8821,
        "longitude": 147.3272,
        "aliases": ["hobart", "hobart tas"],
        "terrain_hint": "mountain",
        "preview_span_km": 18.0,
    },
    {
        "display_name": "Darwin, NT",
        "latitude": -12.4634,
        "longitude": 130.8456,
        "aliases": ["darwin", "darwin nt"],
        "terrain_hint": "open",
        "preview_span_km": 24.0,
    },
    {
        "display_name": "Queenstown, NZ",
        "latitude": -45.0312,
        "longitude": 168.6626,
        "aliases": ["queenstown", "queenstown nz"],
        "terrain_hint": "mountain",
        "preview_span_km": 18.0,
    },
    {
        "display_name": "Christchurch, NZ",
        "latitude": -43.5321,
        "longitude": 172.6362,
        "aliases": ["christchurch", "christchurch nz"],
        "terrain_hint": "mixed",
        "preview_span_km": 22.0,
    },
    {
        "display_name": "San Francisco, CA",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "aliases": ["san francisco", "sf", "san francisco ca"],
        "terrain_hint": "coastal",
        "preview_span_km": 22.0,
    },
    {
        "display_name": "Denver, CO",
        "latitude": 39.7392,
        "longitude": -104.9903,
        "aliases": ["denver", "denver co"],
        "terrain_hint": "mountain",
        "preview_span_km": 22.0,
    },
    {
        "display_name": "Vancouver, BC",
        "latitude": 49.2827,
        "longitude": -123.1207,
        "aliases": ["vancouver", "vancouver bc"],
        "terrain_hint": "forest",
        "preview_span_km": 22.0,
    },
]


def search_location_candidates(query: str | None, *, limit: int = 5) -> list[dict[str, Any]]:
    """Return local-first autocomplete suggestions for place names or coordinates."""

    suggestions: list[dict[str, Any]] = []
    seen: set[tuple[float, float, str]] = set()
    parsed = _parse_coordinate_query(query)
    if parsed is not None:
        candidate = resolve_location_input(latitude=parsed[0], longitude=parsed[1])
        candidate["match_reason"] = "Direct coordinates"
        suggestions.append(candidate)
        seen.add((candidate["latitude"], candidate["longitude"], candidate["display_name"]))

    normalized = _normalize_query(query)
    if not normalized:
        return suggestions[:limit]

    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for entry in LOCAL_GAZETTEER:
        score = _match_score(normalized, _entry_terms(entry))
        if score is None:
            continue
        ranked.append((score, str(entry["display_name"]), entry))

    for _, _, entry in sorted(ranked, key=lambda item: (item[0], item[1])):
        candidate = {
            "display_name": entry["display_name"],
            "latitude": float(entry["latitude"]),
            "longitude": float(entry["longitude"]),
            "source": "local_gazetteer",
            "preview_span_km": float(entry.get("preview_span_km", 18.0)),
            "terrain_hint": str(entry.get("terrain_hint", "mixed")),
            "fallback_note": "Using the built-in local gazetteer. Coordinates remain available for exact mission setup.",
            "match_reason": "Local gazetteer match",
        }
        key = (candidate["latitude"], candidate["longitude"], candidate["display_name"])
        if key in seen:
            continue
        suggestions.append(candidate)
        seen.add(key)
        if len(suggestions) >= limit:
            break
    return suggestions[:limit]


def resolve_location_input(
    query: str | None = None,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict[str, Any]:
    """Resolve a place name or coordinate pair into a local-first location record."""

    parsed = _parse_coordinate_query(query)
    if latitude is not None and longitude is not None:
        lat = float(latitude)
        lon = float(longitude)
        return {
            "display_name": f"{lat:.4f}, {lon:.4f}",
            "latitude": lat,
            "longitude": lon,
            "source": "coordinates",
            "preview_span_km": 18.0,
            "terrain_hint": "mixed",
            "fallback_note": None,
        }
    if parsed is not None:
        lat, lon = parsed
        return {
            "display_name": f"{lat:.4f}, {lon:.4f}",
            "latitude": lat,
            "longitude": lon,
            "source": "coordinates",
            "preview_span_km": 18.0,
            "terrain_hint": "mixed",
            "fallback_note": None,
        }
    normalized = _normalize_query(query)
    if not normalized:
        raise ValueError("Enter a place name or latitude/longitude coordinates.")

    exact = next((entry for entry in LOCAL_GAZETTEER if normalized in _entry_terms(entry)), None)
    if exact is None:
        matches = search_location_candidates(query, limit=1)
        if matches:
            candidate = dict(matches[0])
            candidate.pop("match_reason", None)
            candidate.setdefault(
                "fallback_note",
                "Using the closest built-in gazetteer match. Enter coordinates for an exact area.",
            )
            return candidate
        raise ValueError("Location not found in the local gazetteer. Enter coordinates for an exact area.")
    return {
        "display_name": exact["display_name"],
        "latitude": float(exact["latitude"]),
        "longitude": float(exact["longitude"]),
        "source": "local_gazetteer",
        "preview_span_km": float(exact.get("preview_span_km", 18.0)),
        "terrain_hint": str(exact.get("terrain_hint", "mixed")),
        "fallback_note": "Using the built-in local gazetteer. Enter coordinates for an exact location outside the preset list.",
    }


def preview_mission_area(
    *,
    location: dict[str, Any],
    shape_type: str = "rectangle",
    rectangle: dict[str, float] | None = None,
    polygon: list[dict[str, float]] | None = None,
    grid_resolution_m: float = 500.0,
    staging: dict[str, Any] | None = None,
    last_known_location: dict[str, Any] | None = None,
    weather_summary: dict[str, Any] | None = None,
    last_known_status: str = "unknown",
    environment_type: str = "mixed_terrain",
    weather: str = "clear",
) -> dict[str, Any]:
    """Return normalized mission-area metadata and a terrain preview summary."""

    resolved = resolve_location_input(
        latitude=_safe_float(location.get("latitude")),
        longitude=_safe_float(location.get("longitude")),
    )
    resolved["display_name"] = str(location.get("display_name") or resolved["display_name"])
    resolved["source"] = str(location.get("source") or resolved["source"])
    resolved["terrain_hint"] = str(location.get("terrain_hint") or resolved.get("terrain_hint", "mixed"))
    resolved["preview_span_km"] = float(location.get("preview_span_km") or resolved["preview_span_km"])

    center = {"latitude": resolved["latitude"], "longitude": resolved["longitude"]}
    shape = "polygon" if shape_type == "polygon" and polygon else "rectangle"
    if shape == "polygon":
        normalized_polygon = [_coerce_point(point) for point in polygon or []]
        bounds = _polygon_bounds(normalized_polygon)
        rectangle_payload = {
            "north": bounds["north"],
            "south": bounds["south"],
            "east": bounds["east"],
            "west": bounds["west"],
        }
    else:
        rectangle_payload = _normalize_rectangle(rectangle, center, resolved["preview_span_km"])
        normalized_polygon = _rectangle_to_polygon(rectangle_payload)

    width_km = _east_west_km(rectangle_payload["west"], rectangle_payload["east"], center["latitude"])
    height_km = _north_south_km(rectangle_payload["south"], rectangle_payload["north"])
    area_sq_km = _polygon_area_sq_km(normalized_polygon, center)
    requested_resolution = max(150.0, min(2_000.0, float(grid_resolution_m)))
    resolution_m = requested_resolution
    grid_width = max(MIN_GRID_WIDTH, int(round((width_km * 1000.0) / resolution_m)))
    grid_height = max(MIN_GRID_HEIGHT, int(round((height_km * 1000.0) / resolution_m)))
    warnings: list[str] = []
    if grid_width * grid_height > MAX_SAFE_CELLS:
        scale = sqrt((grid_width * grid_height) / MAX_SAFE_CELLS)
        resolution_m = requested_resolution * scale
        grid_width = max(MIN_GRID_WIDTH, int(round((width_km * 1000.0) / resolution_m)))
        grid_height = max(MIN_GRID_HEIGHT, int(round((height_km * 1000.0) / resolution_m)))
        warnings.append(
            "Resolution was relaxed slightly to keep the grid inside the safe local planning range."
        )

    mission_area: dict[str, Any] = {
        "location_display_name": resolved["display_name"],
        "location_source": resolved["source"],
        "location_query": str(location.get("query") or resolved["display_name"]),
        "center": center,
        "preview_span_km": resolved["preview_span_km"],
        "shape_type": shape,
        "rectangle": rectangle_payload,
        "polygon": normalized_polygon,
        "bounds": {
            "north": rectangle_payload["north"],
            "south": rectangle_payload["south"],
            "east": rectangle_payload["east"],
            "west": rectangle_payload["west"],
        },
        "width_km": round(width_km, 2),
        "height_km": round(height_km, 2),
        "area_sq_km": round(area_sq_km, 2),
        "shape_ratio": round(max(width_km, height_km) / max(min(width_km, height_km), 0.1), 2),
        "requested_grid_resolution_m": round(requested_resolution, 1),
        "grid_resolution_m": round(resolution_m, 1),
        "cell_size_m": round(resolution_m, 1),
        "grid_size": [grid_width, grid_height],
        "grid_cols": grid_width,
        "grid_rows": grid_height,
        "max_safe_cells": MAX_SAFE_CELLS,
        "warnings": warnings,
        "terrain_hint": resolved["terrain_hint"],
        "requested_environment_type": environment_type,
        "last_known_status": last_known_status,
        "environment_type": environment_type,
        "weather_summary": dict(weather_summary or {"recommended_weather": weather, "source": "manual"}),
    }
    mission_area["center_grid_position"] = [grid_width // 2, grid_height // 2]
    mission_area["shape_summary"] = (
        "Irregular polygon AOI" if shape == "polygon" else "Rectangle AOI"
    )
    mission_area["aoi_outline_grid"] = _polygon_to_grid_outline(
        normalized_polygon,
        mission_area,
    )

    staging_point = _normalize_staging_point(staging, mission_area)
    mission_area["staging"] = staging_point
    mission_area["staging_distance_to_center_km"] = round(
        _distance_km(staging_point, center),
        2,
    )
    mission_area["staging_summary"] = _staging_summary(staging_point, mission_area)
    known_point = _normalize_last_known_point(last_known_location, mission_area)
    mission_area["last_known_location"] = known_point
    mission_area["last_known_inside_aoi"] = _point_inside_aoi(known_point, mission_area) if known_point else None
    mission_area["last_known_grid_position"] = list(
        _point_to_grid(
            known_point or center,
            mission_area,
        )
    )
    mission_area["last_known_summary"] = (
        "Last known point is placed inside the search area."
        if known_point and mission_area["last_known_inside_aoi"]
        else "Last known point is set just outside the current search area."
        if known_point
        else "Last known point still needs placement on the map."
        if last_known_status == "known"
        else "No last known point is being used for this mission."
    )
    mission_area["area_metrics_summary"] = (
        f"AOI covers about {area_sq_km:.1f} km^2 across "
        f"{width_km:.1f} by {height_km:.1f} km at roughly {resolution_m:.0f} m cells."
    )
    mission_area["operator_summary"] = mission_area["area_metrics_summary"]
    mission_area["grid_summary"] = {
        "map_size": [grid_width, grid_height],
        "cell_size_m": round(resolution_m, 1),
        "shape_label": mission_area["shape_summary"],
        "operator_summary": (
            f"Grid resolves to {grid_width} by {grid_height} cells."
        ),
    }
    mission_area["area_metrics"] = {
        "area_sq_km": round(area_sq_km, 2),
        "width_km": round(width_km, 2),
        "height_km": round(height_km, 2),
        "grid_cols": grid_width,
        "grid_rows": grid_height,
        "grid_resolution_m": round(resolution_m, 1),
        "staging_offset_km": mission_area["staging_distance_to_center_km"],
        "last_known_inside_aoi": mission_area["last_known_inside_aoi"],
        "operator_summary": (
            f"{mission_area['area_metrics_summary']} {mission_area['grid_summary']['operator_summary']}"
        ),
    }

    terrain_preview = derive_mission_area_layers(
        mission_area,
        scenario_family=environment_type,
        weather=weather,
    )
    mission_area["terrain_summary"] = terrain_preview["terrain_summary"]
    mission_area["terrain_burden_summary"] = terrain_preview["terrain_summary"]["terrain_burden_summary"]
    mission_area["slope_summary"] = terrain_preview["terrain_summary"]["slope_summary"]
    mission_area["slope_elevation_summary"] = terrain_preview["terrain_summary"]["slope_summary"]["operator_summary"]
    environment_summary = _environment_summary(terrain_preview["terrain_summary"])
    mission_area["environment_summary"] = environment_summary
    mission_area["environment_type"] = environment_summary["value"]
    mission_area["environment_label"] = environment_summary["label"]
    mission_area["planner_ready"] = bool(
        not warnings and (last_known_status != "known" or known_point is not None)
    )
    mission_area["planner_status_summary"] = _planner_status_summary(mission_area)
    mission_area["context_summary"] = _context_summary(mission_area)
    return mission_area


def derive_mission_area_layers(
    mission_area: dict[str, Any],
    *,
    scenario_family: str,
    weather: str,
) -> dict[str, Any]:
    """Derive deterministic terrain, obstacle, trail, elevation, and wind layers."""

    width, height = [int(value) for value in mission_area.get("grid_size", [18, 14])]
    width = max(MIN_GRID_WIDTH, width)
    height = max(MIN_GRID_HEIGHT, height)
    center = mission_area.get("center", {})
    terrain_hint = str(mission_area.get("terrain_hint") or "mixed")
    scenario_family = str(scenario_family or mission_area.get("environment_type") or "mixed_terrain")
    seed = _stable_seed(_safe_float(center.get("latitude"), 0.0), _safe_float(center.get("longitude"), 0.0))
    rng = np.random.default_rng(seed)

    y_axis, x_axis = np.mgrid[0:height, 0:width]
    xx = x_axis / max(width - 1, 1)
    yy = y_axis / max(height - 1, 1)
    angle = rng.uniform(0.25, 2.75)
    phase_a = rng.uniform(0, 2 * pi)
    phase_b = rng.uniform(0, 2 * pi)
    phase_c = rng.uniform(0, 2 * pi)
    axis_primary = xx * np.cos(angle) + yy * np.sin(angle)
    axis_secondary = xx * np.sin(angle) - yy * np.cos(angle)
    ridge = np.sin(axis_primary * pi * (1.6 + rng.uniform(0.0, 0.9)) + phase_a)
    basin = np.cos(axis_secondary * pi * (1.2 + rng.uniform(0.0, 0.8)) + phase_b)
    distance = np.hypot(xx - 0.5, yy - 0.5)
    vegetation_signal = np.sin(xx * pi * 2.3 + phase_c) * np.cos(yy * pi * 2.0 + phase_b / 2.0)

    hint_ruggedness = {
        "mountain": 0.95,
        "forest": 0.7,
        "coastal": 0.45,
        "open": 0.35,
        "urban": 0.28,
        "mixed": 0.55,
    }.get(terrain_hint, 0.55)
    family_ruggedness = {
        "open_terrain": 0.3,
        "mixed_terrain": 0.55,
        "dense_forest": 0.65,
        "obstacle_heavy": 0.72,
        "poor_comms": 0.5,
    }.get(scenario_family, 0.55)
    ruggedness = max(hint_ruggedness, family_ruggedness)

    elevation_seed = 0.55 + 0.32 * ridge + 0.24 * basin - 0.18 * distance + 0.1 * vegetation_signal
    elevation_normalized = _normalize_array(elevation_seed)
    elevation_scale = 180.0 + 620.0 * ruggedness + 55.0 * sqrt(max(float(mission_area.get("area_sq_km", 1.0)), 1.0))
    elevation_layer = elevation_normalized * elevation_scale

    grad_y, grad_x = np.gradient(elevation_layer)
    slope = _normalize_array(np.hypot(grad_x, grad_y))
    mean_slope = float(np.mean(slope))

    river_center = 0.42 + 0.12 * np.sin(xx * pi * (1.4 + rng.uniform(0.0, 0.7)) + phase_a / 2.0)
    river_width = 0.03 + 0.04 * (1.0 - elevation_normalized)
    river_mask = np.abs(yy - river_center) < river_width
    edge_distance = np.minimum.reduce([xx, yy, 1.0 - xx, 1.0 - yy])
    coastal_mask = (elevation_normalized < 0.16) & (edge_distance < 0.12)
    water_mask = river_mask | coastal_mask

    aoi_mask = _build_aoi_mask(mission_area, width, height)
    water_mask &= aoi_mask

    staging_grid = tuple(
        int(value) for value in (mission_area.get("staging", {}).get("grid_position") or [width // 2, height - 2])
    )
    staging_x = staging_grid[0] / max(width - 1, 1)
    staging_y = staging_grid[1] / max(height - 1, 1)
    staging_focus = np.exp(-(((xx - staging_x) ** 2) + ((yy - staging_y) ** 2)) / 0.03)
    urban_bias = terrain_hint == "urban" or scenario_family == "obstacle_heavy"
    urban_mask = (staging_focus > 0.35) & (slope < 0.55) & ~water_mask
    if not urban_bias:
        urban_mask &= vegetation_signal > -0.15

    forest_bias = terrain_hint in {"forest", "mountain"} or scenario_family == "dense_forest"
    forest_threshold = 0.12 if forest_bias else 0.32
    forest_mask = (vegetation_signal > forest_threshold) & (slope < 0.72) & ~water_mask & ~urban_mask

    hill_threshold = 0.52 if ruggedness >= 0.65 else 0.62
    hill_mask = ((slope > hill_threshold) | (elevation_normalized > 0.72)) & ~water_mask & ~urban_mask

    terrain_grid = np.full((height, width), int(TerrainType.PLAIN), dtype=int)
    terrain_grid[forest_mask] = int(TerrainType.FOREST)
    terrain_grid[hill_mask] = int(TerrainType.HILL)
    terrain_grid[urban_mask] = int(TerrainType.URBAN)
    terrain_grid[water_mask] = int(TerrainType.WATER)

    trail_layer = np.zeros((height, width), dtype=bool)
    center_grid = tuple(int(value) for value in mission_area.get("center_grid_position", [width // 2, height // 2]))
    for line in (
        _line_points(staging_grid, center_grid),
        _line_points((0, min(height - 1, center_grid[1])), (width - 1, min(height - 1, center_grid[1]))),
    ):
        for x, y in line:
            for offset_x, offset_y in ((0, 0), (1, 0), (0, 1), (-1, 0), (0, -1)):
                nx, ny = x + offset_x, y + offset_y
                if 0 <= nx < width and 0 <= ny < height and aoi_mask[ny, nx]:
                    trail_layer[ny, nx] = True

    obstacle_mask = (~aoi_mask) | water_mask
    obstacle_mask |= (slope > 0.86) & hill_mask
    trail_layer &= ~obstacle_mask

    weather_strength = {
        "clear": 0.12,
        "windy": 0.42,
        "rain": 0.28,
        "storm": 0.58,
    }.get(str(weather), 0.22)
    wind_layer = weather_strength * (0.35 + 0.65 * np.abs(np.cos(axis_primary * pi + phase_b)))

    terrain_summary = _terrain_summary(
        terrain_grid=terrain_grid,
        aoi_mask=aoi_mask,
        obstacle_mask=obstacle_mask,
        trail_layer=trail_layer,
        elevation_layer=elevation_layer,
        slope=slope,
        scenario_family=scenario_family,
        source_mode="local_first_deterministic",
    )
    return {
        "terrain_grid": terrain_grid,
        "obstacle_mask": obstacle_mask,
        "trail_layer": trail_layer,
        "elevation_layer": elevation_layer,
        "wind_layer": wind_layer,
        "terrain_summary": terrain_summary,
    }


def build_environment_from_mission_area(
    mission_area: dict[str, Any],
    *,
    scenario_family: str,
    weather: str,
) -> GridEnvironment:
    """Build a GridEnvironment from mission-area metadata."""

    layers = derive_mission_area_layers(mission_area, scenario_family=scenario_family, weather=weather)
    return GridEnvironment.from_layers(
        terrain_grid=layers["terrain_grid"],
        obstacle_mask=layers["obstacle_mask"],
        trail_layer=layers["trail_layer"],
        elevation_layer=layers["elevation_layer"],
        wind_layer=layers["wind_layer"],
        cell_size_m=float(mission_area.get("grid_resolution_m") or mission_area.get("cell_size_m") or 1.0),
    )


def mission_area_operator_text(mission_area: dict[str, Any] | None) -> str:
    """Return a short human-readable AOI summary."""

    if not mission_area:
        return "Synthetic search area"
    return str(
        mission_area.get("context_summary")
        or mission_area.get("operator_summary")
        or mission_area.get("grid_summary", {}).get("operator_summary")
        or "Mission area configured"
    )


def _normalize_query(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower()).strip()


def _entry_terms(entry: dict[str, Any]) -> set[str]:
    values = [entry.get("display_name", ""), *entry.get("aliases", [])]
    return {_normalize_query(str(value)) for value in values if str(value).strip()}


def _match_score(normalized_query: str, terms: set[str]) -> int | None:
    if normalized_query in terms:
        return 0
    if any(term.startswith(normalized_query) for term in terms):
        return 1
    if any(normalized_query in term for term in terms):
        return 2
    return None


def _parse_coordinate_query(query: str | None) -> tuple[float, float] | None:
    if not query:
        return None
    match = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)\s*$", query)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def _coerce_point(value: dict[str, Any]) -> dict[str, float]:
    return {
        "latitude": _safe_float(value.get("latitude") or value.get("lat")),
        "longitude": _safe_float(value.get("longitude") or value.get("lon")),
    }


def _normalize_rectangle(
    rectangle: dict[str, float] | None,
    center: dict[str, float],
    preview_span_km: float,
) -> dict[str, float]:
    if rectangle and {"north", "south", "east", "west"} <= set(rectangle):
        north = max(float(rectangle["north"]), float(rectangle["south"]))
        south = min(float(rectangle["north"]), float(rectangle["south"]))
        east = max(float(rectangle["east"]), float(rectangle["west"]))
        west = min(float(rectangle["east"]), float(rectangle["west"]))
        return {"north": north, "south": south, "east": east, "west": west}

    width_km = max(4.0, preview_span_km * 0.55)
    height_km = max(3.0, preview_span_km * 0.4)
    lat_delta = height_km / _km_per_degree_lat()
    lon_delta = width_km / _km_per_degree_lon(center["latitude"])
    return {
        "north": center["latitude"] + lat_delta / 2.0,
        "south": center["latitude"] - lat_delta / 2.0,
        "east": center["longitude"] + lon_delta / 2.0,
        "west": center["longitude"] - lon_delta / 2.0,
    }


def _rectangle_to_polygon(rectangle: dict[str, float]) -> list[dict[str, float]]:
    return [
        {"latitude": rectangle["north"], "longitude": rectangle["west"]},
        {"latitude": rectangle["north"], "longitude": rectangle["east"]},
        {"latitude": rectangle["south"], "longitude": rectangle["east"]},
        {"latitude": rectangle["south"], "longitude": rectangle["west"]},
    ]


def _polygon_bounds(points: list[dict[str, float]]) -> dict[str, float]:
    latitudes = [point["latitude"] for point in points]
    longitudes = [point["longitude"] for point in points]
    return {
        "north": max(latitudes),
        "south": min(latitudes),
        "east": max(longitudes),
        "west": min(longitudes),
    }


def _polygon_area_sq_km(points: list[dict[str, float]], center: dict[str, float]) -> float:
    if len(points) < 3:
        return 0.0
    projected = [_project_km(point, center) for point in points]
    total = 0.0
    for index, (x1, y1) in enumerate(projected):
        x2, y2 = projected[(index + 1) % len(projected)]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def _project_km(point: dict[str, float], center: dict[str, float]) -> tuple[float, float]:
    lat = float(point["latitude"])
    lon = float(point["longitude"])
    center_lat = float(center["latitude"])
    center_lon = float(center["longitude"])
    return (
        (lon - center_lon) * _km_per_degree_lon(center_lat),
        (lat - center_lat) * _km_per_degree_lat(),
    )


def _normalize_staging_point(staging: dict[str, Any] | None, mission_area: dict[str, Any]) -> dict[str, Any]:
    bounds = mission_area["bounds"]
    center_lon = (bounds["west"] + bounds["east"]) / 2.0
    default_lat = bounds["south"] + (bounds["north"] - bounds["south"]) * 0.08
    normalized = {
        "latitude": _safe_float(staging.get("latitude")) if staging else default_lat,
        "longitude": _safe_float(staging.get("longitude")) if staging else center_lon,
        "label": str(staging.get("label") or "Primary staging point") if staging else "Primary staging point",
        "placement": str(staging.get("placement") or "map") if staging else "default_edge",
    }
    normalized["grid_position"] = list(_point_to_grid(normalized, mission_area))
    return normalized


def _normalize_last_known_point(
    last_known_location: dict[str, Any] | None,
    mission_area: dict[str, Any],
) -> dict[str, Any] | None:
    if not last_known_location:
        return None
    latitude = last_known_location.get("latitude")
    longitude = last_known_location.get("longitude")
    if latitude is None or longitude is None:
        return None
    normalized = {
        "latitude": _safe_float(latitude),
        "longitude": _safe_float(longitude),
        "label": str(last_known_location.get("label") or "Last known location"),
        "placement": str(last_known_location.get("placement") or "map"),
    }
    normalized["grid_position"] = list(_point_to_grid(normalized, mission_area))
    return normalized


def _point_inside_aoi(point: dict[str, Any] | None, mission_area: dict[str, Any]) -> bool:
    if not point:
        return False
    bounds = mission_area["bounds"]
    latitude = float(point["latitude"])
    longitude = float(point["longitude"])
    return (
        bounds["south"] <= latitude <= bounds["north"]
        and bounds["west"] <= longitude <= bounds["east"]
    )


def _staging_summary(staging_point: dict[str, Any], mission_area: dict[str, Any]) -> str:
    bounds = mission_area["bounds"]
    latitude = float(staging_point["latitude"])
    longitude = float(staging_point["longitude"])
    vertical = ""
    horizontal = ""
    if latitude > bounds["north"]:
        vertical = "north of"
    elif latitude < bounds["south"]:
        vertical = "south of"
    if longitude > bounds["east"]:
        horizontal = "east of"
    elif longitude < bounds["west"]:
        horizontal = "west of"
    if vertical and horizontal:
        return f"Base is positioned {vertical} and {horizontal} the search area."
    if vertical:
        return f"Base is positioned just {vertical} the search area."
    if horizontal:
        return f"Base is positioned just {horizontal} the search area."
    return "Base is positioned inside the selected search area."


def _point_to_grid(point: dict[str, Any], mission_area: dict[str, Any]) -> tuple[int, int]:
    bounds = mission_area["bounds"]
    width, height = [int(value) for value in mission_area.get("grid_size", [18, 14])]
    lon_span = max(bounds["east"] - bounds["west"], 1e-9)
    lat_span = max(bounds["north"] - bounds["south"], 1e-9)
    x = int(round(((float(point["longitude"]) - bounds["west"]) / lon_span) * (width - 1)))
    y = int(round(((bounds["north"] - float(point["latitude"])) / lat_span) * (height - 1)))
    return max(0, min(width - 1, x)), max(0, min(height - 1, y))


def _polygon_to_grid_outline(
    polygon: list[dict[str, float]],
    mission_area: dict[str, Any],
) -> list[list[int]]:
    if len(polygon) < 2:
        return []

    grid_points = [_point_to_grid(point, mission_area) for point in polygon]
    outline: list[list[int]] = []
    pairs = list(zip(grid_points, grid_points[1:] + [grid_points[0]]))
    for start, end in pairs:
        for x, y in _line_points(start, end):
            point = [int(x), int(y)]
            if not outline or outline[-1] != point:
                outline.append(point)
    if outline and outline[0] != outline[-1]:
        outline.append(list(outline[0]))
    return outline


def _build_aoi_mask(mission_area: dict[str, Any], width: int, height: int) -> np.ndarray:
    if mission_area.get("shape_type") != "polygon":
        return np.ones((height, width), dtype=bool)
    polygon = [_coerce_point(point) for point in mission_area.get("polygon", [])]
    if len(polygon) < 3:
        return np.ones((height, width), dtype=bool)

    local_polygon = []
    bounds = mission_area["bounds"]
    lon_span = max(bounds["east"] - bounds["west"], 1e-9)
    lat_span = max(bounds["north"] - bounds["south"], 1e-9)
    for point in polygon:
        local_polygon.append(
            (
                (point["longitude"] - bounds["west"]) / lon_span,
                (bounds["north"] - point["latitude"]) / lat_span,
            )
        )

    mask = np.zeros((height, width), dtype=bool)
    for y in range(height):
        py = (y + 0.5) / max(height, 1)
        for x in range(width):
            px = (x + 0.5) / max(width, 1)
            mask[y, x] = _point_in_polygon(px, py, local_polygon)
    return mask


def _point_in_polygon(x: float, y: float, polygon: list[tuple[float, float]]) -> bool:
    inside = False
    count = len(polygon)
    for index in range(count):
        x1, y1 = polygon[index]
        x2, y2 = polygon[(index + 1) % count]
        intersects = ((y1 > y) != (y2 > y)) and (
            x < (x2 - x1) * (y - y1) / max((y2 - y1), 1e-9) + x1
        )
        if intersects:
            inside = not inside
    return inside


def _line_points(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
    x1, y1 = start
    x2, y2 = end
    points: list[tuple[int, int]] = []
    dx = abs(x2 - x1)
    dy = -abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx + dy
    while True:
        points.append((x1, y1))
        if x1 == x2 and y1 == y2:
            break
        err2 = 2 * err
        if err2 >= dy:
            err += dy
            x1 += sx
        if err2 <= dx:
            err += dx
            y1 += sy
    return points


def _terrain_summary(
    *,
    terrain_grid: np.ndarray,
    aoi_mask: np.ndarray,
    obstacle_mask: np.ndarray,
    trail_layer: np.ndarray,
    elevation_layer: np.ndarray,
    slope: np.ndarray,
    scenario_family: str,
    source_mode: str,
) -> dict[str, Any]:
    terrain_names = {
        int(TerrainType.PLAIN): "open terrain",
        int(TerrainType.FOREST): "forest",
        int(TerrainType.HILL): "hill country",
        int(TerrainType.URBAN): "urban edge",
        int(TerrainType.WATER): "water / no-go",
    }
    selected = terrain_grid[aoi_mask]
    total = max(int(selected.size), 1)
    mix = {
        terrain_names[int(code)]: round(float(np.count_nonzero(selected == int(code))) / total, 3)
        for code in TerrainType
    }
    dominant = max(mix.items(), key=lambda item: item[1])[0]
    elevation_values = elevation_layer[aoi_mask]
    slope_values = slope[aoi_mask]
    obstacle_pct = float(np.count_nonzero(obstacle_mask & aoi_mask)) / total
    trail_pct = float(np.count_nonzero(trail_layer & aoi_mask)) / total
    mean_slope = float(np.mean(slope_values)) if slope_values.size else 0.0
    slope_burden = (
        "elevated" if mean_slope >= 0.48 else "moderate" if mean_slope >= 0.28 else "light"
    )
    trail_access = "good" if trail_pct >= 0.12 else "limited" if trail_pct <= 0.05 else "workable"
    suggested_family = scenario_family
    if mix["forest"] >= 0.38:
        suggested_family = "dense_forest"
    elif mix["open terrain"] >= 0.55 and mix["urban edge"] <= 0.14:
        suggested_family = "open_terrain"
    elif mix["urban edge"] >= 0.22 or obstacle_pct >= 0.22:
        suggested_family = "obstacle_heavy"
    elif slope_burden == "elevated":
        suggested_family = "mixed_terrain"

    terrain_burden = _terrain_burden_summary(
        dominant=dominant,
        terrain_mix=mix,
        slope_burden=slope_burden,
        trail_access=trail_access,
        obstacle_pct=obstacle_pct,
    )
    slope_summary = _slope_elevation_summary(
        slope_burden=slope_burden,
        elevation_min=float(np.min(elevation_values)) if elevation_values.size else 0.0,
        elevation_max=float(np.max(elevation_values)) if elevation_values.size else 0.0,
    )
    operator_summary = (
        f"The selected area reads as {terrain_burden['label'].lower()}, with "
        f"{slope_summary['label'].lower()} and {trail_access} access."
    )
    return {
        "source_mode": source_mode,
        "dominant_terrain": dominant,
        "terrain_mix": mix,
        "elevation_range_m": [
            round(float(np.min(elevation_values)) if elevation_values.size else 0.0, 1),
            round(float(np.max(elevation_values)) if elevation_values.size else 0.0, 1),
        ],
        "mean_elevation_m": round(float(np.mean(elevation_values)) if elevation_values.size else 0.0, 1),
        "slope_burden": slope_burden,
        "trail_access": trail_access,
        "trail_coverage_pct": round(trail_pct, 3),
        "obstacle_coverage_pct": round(obstacle_pct, 3),
        "water_coverage_pct": round(mix.get("water / no-go", 0.0), 3),
        "suggested_scenario_family": suggested_family,
        "terrain_burden_label": terrain_burden["label"],
        "terrain_burden_summary": terrain_burden["operator_summary"],
        "slope_summary": slope_summary,
        "operator_summary": operator_summary,
    }


def _environment_summary(terrain_summary: dict[str, Any]) -> dict[str, str]:
    dominant = str(terrain_summary.get("dominant_terrain") or "")
    slope_burden = str(terrain_summary.get("slope_burden") or "light")
    obstacle_pct = float(terrain_summary.get("obstacle_coverage_pct", 0.0) or 0.0)
    terrain_burden_label = str(terrain_summary.get("terrain_burden_label") or "")

    value = "mixed_terrain"
    label = "Mixed terrain"
    operator_summary = "Mixed terrain is the best overall description for the selected area."

    if dominant == "forest" and slope_burden == "elevated":
        value = "dense_forest"
        label = "Forested hill country"
        operator_summary = "Forested hill country is the dominant character of the selected area."
    elif dominant == "forest":
        value = "dense_forest"
        label = "Forested"
        operator_summary = "Forested terrain is the dominant character of the selected area."
    elif dominant == "urban edge" or obstacle_pct >= 0.22:
        value = "obstacle_heavy"
        label = "Obstacle-heavy"
        operator_summary = "Obstacle-heavy ground is the dominant character of the selected area."
    elif dominant == "open terrain" and slope_burden == "light":
        value = "open_terrain"
        label = "Open terrain"
        operator_summary = "Open terrain is the dominant character of the selected area."
    elif slope_burden == "elevated":
        value = "mixed_terrain"
        label = "Elevated mixed terrain"
        operator_summary = "Elevated ground is a defining feature of the selected area."
    elif slope_burden == "moderate":
        value = "mixed_terrain"
        label = "Mixed terrain with moderate slope"
        operator_summary = "Mixed terrain with moderate slope best describes the selected area."

    if terrain_burden_label == "Water-constrained terrain":
        value = "mixed_terrain"
        label = "Water-constrained mixed terrain"
        operator_summary = "Water and no-go terrain are a defining planning constraint in the selected area."

    return {
        "value": value,
        "label": label,
        "operator_summary": operator_summary,
    }


def _terrain_burden_summary(
    *,
    dominant: str,
    terrain_mix: dict[str, float],
    slope_burden: str,
    trail_access: str,
    obstacle_pct: float,
) -> dict[str, str]:
    forest_pct = float(terrain_mix.get("forest", 0.0) or 0.0)
    open_pct = float(terrain_mix.get("open terrain", 0.0) or 0.0)
    water_pct = float(terrain_mix.get("water / no-go", 0.0) or 0.0)

    if water_pct >= 0.18:
        return {
            "label": "Water-constrained terrain",
            "operator_summary": "Water and no-go areas carve up the search box and constrain clean coverage lines.",
        }
    if dominant == "forest" and trail_access == "good":
        return {
            "label": "Forested with access corridors",
            "operator_summary": "Forested ground dominates, but access corridors should help staging and repositioning.",
        }
    if dominant == "forest":
        return {
            "label": "Forested / dense vegetation",
            "operator_summary": "Dense vegetation will slow broad coverage and create a heavier inspect-and-confirm burden.",
        }
    if dominant == "hill country" and trail_access == "good":
        return {
            "label": "Trail-accessible hill country",
            "operator_summary": "Hill country dominates, but usable access corridors should help movement and recovery routes.",
        }
    if dominant == "hill country":
        return {
            "label": "Elevated hill country",
            "operator_summary": "Elevated ground is a strong planning constraint and will stretch coverage pacing.",
        }
    if dominant == "urban edge" or obstacle_pct >= 0.22:
        return {
            "label": "Obstacle-heavy terrain",
            "operator_summary": "Obstacle-heavy ground will break up clean lane coverage and make sectoring more useful.",
        }
    if dominant == "open terrain" and forest_pct >= 0.18:
        return {
            "label": "Open with moderate cover",
            "operator_summary": "Most of the area is open, with enough cover to interrupt visibility in parts of the search box.",
        }
    if trail_access == "good":
        return {
            "label": "Mixed terrain with clear access corridors",
            "operator_summary": "Mixed terrain dominates, but access corridors should help staging and search recovery.",
        }
    if dominant == "open terrain" and slope_burden == "light":
        return {
            "label": "Open terrain",
            "operator_summary": "Open ground should support cleaner lanes, simpler monitoring, and steadier returns to base.",
        }
    if open_pct >= 0.45:
        return {
            "label": "Open terrain with moderate cover",
            "operator_summary": "The area is mostly open, but enough cover remains to justify a balanced search layout.",
        }
    return {
        "label": "Mixed terrain",
        "operator_summary": "Mixed terrain will require a balanced search layout rather than a highly specialized one.",
    }


def _slope_elevation_summary(
    *,
    slope_burden: str,
    elevation_min: float,
    elevation_max: float,
) -> dict[str, str]:
    elevation_range = max(0.0, elevation_max - elevation_min)
    if slope_burden == "elevated" and elevation_range >= 420.0:
        return {
            "value": "steep",
            "label": "Steep terrain",
            "operator_summary": "Steep terrain will slow coverage, stretch returns to base, and justify stronger reserve margin.",
        }
    if slope_burden == "elevated":
        return {
            "value": "elevated",
            "label": "Elevated hill country",
            "operator_summary": "Hillier ground will tighten battery pacing and slow systematic coverage.",
        }
    if slope_burden == "moderate" and elevation_range >= 240.0:
        return {
            "value": "mixed",
            "label": "Mixed elevation profile",
            "operator_summary": "The area has a mixed elevation profile, so some sectors will search more slowly than others.",
        }
    if slope_burden == "moderate":
        return {
            "value": "moderate",
            "label": "Moderate slope burden",
            "operator_summary": "Moderate slope should be manageable, but it will still soften ideal lane coverage.",
        }
    return {
        "value": "low",
        "label": "Low slope burden",
        "operator_summary": "Relatively gentle ground should support cleaner coverage and simpler returns to base.",
    }


def _planner_status_summary(mission_area: dict[str, Any]) -> str:
    if mission_area.get("last_known_status") == "known" and not mission_area.get("last_known_location"):
        return "Planning context is almost ready. Place the last known point to tighten the opening search."
    warnings = list(mission_area.get("warnings") or [])
    if warnings:
        return "Planning context is ready, but review the grid warning before launch."
    return "Planning context is ready for recommendation and simulation."


def _context_summary(mission_area: dict[str, Any]) -> str:
    environment = mission_area.get("environment_summary", {})
    slope_summary = mission_area.get("slope_summary", {})
    weather_summary = mission_area.get("weather_summary", {})
    location_name = str(mission_area.get("location_display_name") or "Selected mission area").strip()
    parts = [
        f"Location: {location_name}.",
        str(mission_area.get("area_metrics_summary") or mission_area.get("operator_summary") or "").strip(),
        str(mission_area.get("grid_summary", {}).get("operator_summary") or "").strip(),
        f"Environment reads as {str(environment.get('label') or 'mixed terrain').lower()}.".strip(),
        str(mission_area.get("terrain_burden_summary") or "").strip(),
        str(slope_summary.get("operator_summary") or "").strip(),
        str(mission_area.get("staging_summary") or "").strip(),
        str(mission_area.get("last_known_summary") or "").strip(),
        str(weather_summary.get("operator_summary") or "").strip(),
        str(mission_area.get("planner_status_summary") or "").strip(),
    ]
    return " ".join(part for part in parts if part)


def _normalize_array(values: np.ndarray) -> np.ndarray:
    minimum = float(np.min(values))
    maximum = float(np.max(values))
    if maximum - minimum <= 1e-9:
        return np.zeros_like(values, dtype=float)
    return (values - minimum) / (maximum - minimum)


def _km_per_degree_lat() -> float:
    return 111.32


def _km_per_degree_lon(latitude: float) -> float:
    return max(111.32 * cos(radians(latitude)), 0.1)


def _north_south_km(south: float, north: float) -> float:
    return abs(north - south) * _km_per_degree_lat()


def _east_west_km(west: float, east: float, latitude: float) -> float:
    return abs(east - west) * _km_per_degree_lon(latitude)


def _distance_km(point_a: dict[str, Any], point_b: dict[str, Any]) -> float:
    dy = (float(point_a["latitude"]) - float(point_b["latitude"])) * _km_per_degree_lat()
    dx = (float(point_a["longitude"]) - float(point_b["longitude"])) * _km_per_degree_lon(
        (float(point_a["latitude"]) + float(point_b["latitude"])) / 2.0
    )
    return sqrt(dx * dx + dy * dy)


def _safe_float(value: Any, fallback: float | None = None) -> float:
    if value is None:
        if fallback is None:
            raise ValueError("Missing numeric value.")
        return fallback
    return float(value)


def _stable_seed(latitude: float, longitude: float) -> int:
    lat_term = int(round((latitude + 90.0) * 10_000))
    lon_term = int(round((longitude + 180.0) * 10_000))
    return (lat_term * 2_654_435_761 + lon_term * 1_597_334_677) & 0xFFFFFFFF
