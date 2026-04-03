"""Connected geospatial helpers with graceful local-first fallback."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from math import sin
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.backend.core.settings import BackendSettings
from src.environment.mission_area import (
    preview_mission_area,
    resolve_location_input,
    search_location_candidates,
)


WEATHER_CODE_LABELS: dict[int, tuple[str, str]] = {
    0: ("clear", "Clear"),
    1: ("clear", "Mostly clear"),
    2: ("windy", "Partly cloudy"),
    3: ("windy", "Overcast"),
    45: ("windy", "Fog"),
    48: ("windy", "Freezing fog"),
    51: ("rain", "Light drizzle"),
    53: ("rain", "Drizzle"),
    55: ("rain", "Heavy drizzle"),
    61: ("rain", "Light rain"),
    63: ("rain", "Rain"),
    65: ("rain", "Heavy rain"),
    66: ("storm", "Freezing rain"),
    67: ("storm", "Heavy freezing rain"),
    71: ("storm", "Snow"),
    73: ("storm", "Heavy snow"),
    75: ("storm", "Blizzard conditions"),
    80: ("rain", "Rain showers"),
    81: ("rain", "Heavy showers"),
    82: ("storm", "Violent rain showers"),
    95: ("storm", "Thunderstorm"),
    96: ("storm", "Thunderstorm with hail"),
    99: ("storm", "Severe thunderstorm"),
}


class GeospatialService:
    """Resolve mission locations, preview AOI-backed metadata, and fetch weather."""

    def __init__(self, settings: BackendSettings) -> None:
        self.settings = settings

    def search_locations(self, request: dict[str, Any]) -> dict[str, Any]:
        query = str(request.get("query") or "").strip()
        limit = max(1, min(int(request.get("limit", 5) or 5), 8))
        items = search_location_candidates(query, limit=limit)
        if self.settings.enable_live_geocoder and query and len(items) < limit:
            items = self._merge_candidates(items, self._remote_search(query, limit=limit - len(items)))
        return {"items": items[:limit]}

    def resolve_location(self, request: dict[str, Any]) -> dict[str, Any]:
        try:
            return resolve_location_input(
                query=request.get("query"),
                latitude=request.get("latitude"),
                longitude=request.get("longitude"),
            )
        except ValueError:
            if not self.settings.enable_live_geocoder:
                raise
            query = str(request.get("query") or "").strip()
            remote = self._remote_search(query, limit=1)
            if remote:
                resolved = dict(remote[0])
                resolved.pop("match_reason", None)
                return resolved
            raise

    def preview_area(self, request: dict[str, Any]) -> dict[str, Any]:
        location = dict(request.get("location") or {})
        mission_area = preview_mission_area(
            location=location,
            shape_type=str(request.get("shape_type", "rectangle")),
            rectangle=request.get("rectangle"),
            polygon=request.get("polygon"),
            grid_resolution_m=float(request.get("grid_resolution_m", 500.0)),
            staging=request.get("staging"),
            last_known_location=request.get("last_known_location"),
            weather_summary=request.get("weather_summary"),
            last_known_status=str(request.get("last_known_status", "unknown")),
            environment_type=str(request.get("environment_type", "mixed_terrain")),
            weather=str(request.get("weather", "clear")),
        )
        return {"mission_area": mission_area}

    def current_weather(self, request: dict[str, Any]) -> dict[str, Any]:
        latitude = float(request.get("latitude"))
        longitude = float(request.get("longitude"))
        if self.settings.enable_live_weather:
            live = self._fetch_live_weather(latitude, longitude)
            if live is not None:
                return live
        return self._fallback_weather(latitude, longitude)

    def _remote_search(self, query: str, *, limit: int) -> list[dict[str, Any]]:
        if not query:
            return []
        try:
            params = urlencode({"format": "jsonv2", "limit": limit, "q": query})
            request = Request(
                f"{self.settings.geocoder_endpoint}?{params}",
                headers={"User-Agent": "swarm-search-sim/1.0"},
            )
            with urlopen(request, timeout=self.settings.geospatial_timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []

        suggestions: list[dict[str, Any]] = []
        for item in payload[:limit]:
            try:
                latitude = float(item["lat"])
                longitude = float(item["lon"])
            except Exception:
                continue
            display_name = str(item.get("display_name") or query)
            suggestions.append(
                {
                    "display_name": display_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "source": "live_geocoder",
                    "provider": "nominatim",
                    "preview_span_km": 18.0,
                    "terrain_hint": "mixed",
                    "fallback_note": None,
                    "match_reason": "Live geocoder match",
                }
            )
        return suggestions

    def _merge_candidates(
        self,
        base: list[dict[str, Any]],
        extra: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged = list(base)
        seen = {
            (
                round(float(item.get("latitude", 0.0)), 5),
                round(float(item.get("longitude", 0.0)), 5),
                str(item.get("display_name", "")),
            )
            for item in base
        }
        for item in extra:
            key = (
                round(float(item.get("latitude", 0.0)), 5),
                round(float(item.get("longitude", 0.0)), 5),
                str(item.get("display_name", "")),
            )
            if key in seen:
                continue
            merged.append(item)
            seen.add(key)
        return merged

    def _fetch_live_weather(self, latitude: float, longitude: float) -> dict[str, Any] | None:
        params = urlencode(
            {
                "latitude": f"{latitude:.5f}",
                "longitude": f"{longitude:.5f}",
                "current": "temperature_2m,wind_speed_10m,precipitation,cloud_cover,weather_code",
                "timezone": "auto",
            }
        )
        try:
            request = Request(
                f"{self.settings.weather_endpoint}?{params}",
                headers={"User-Agent": "swarm-search-sim/1.0"},
            )
            with urlopen(request, timeout=self.settings.geospatial_timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            current = payload.get("current", {})
            weather_code = int(current.get("weather_code", 0) or 0)
            recommended_weather, label = WEATHER_CODE_LABELS.get(weather_code, ("clear", "Clear"))
            wind_speed = float(current.get("wind_speed_10m", 0.0) or 0.0)
            precipitation = float(current.get("precipitation", 0.0) or 0.0)
            cloud_cover = float(current.get("cloud_cover", 0.0) or 0.0)
            if wind_speed >= 30.0 and recommended_weather == "clear":
                recommended_weather = "windy"
            visibility_label = "Reduced" if cloud_cover >= 85.0 or precipitation >= 1.0 else "Good"
            return {
                "source": "live_weather",
                "provider": "open-meteo",
                "recommended_weather": recommended_weather,
                "condition_label": label,
                "temperature_c": round(float(current.get("temperature_2m", 0.0) or 0.0), 1),
                "wind_speed_kph": round(wind_speed, 1),
                "precipitation_mm": round(precipitation, 2),
                "cloud_cover_pct": round(cloud_cover, 1),
                "visibility_label": visibility_label,
                "operator_summary": (
                    f"Current weather shows {label.lower()} with winds around {wind_speed:.0f} kph."
                ),
                "fallback_note": None,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception:
            return None

    def _fallback_weather(self, latitude: float, longitude: float) -> dict[str, Any]:
        seed = abs(sin(latitude * 0.31 + longitude * 0.19))
        wind_speed = round(10.0 + seed * 22.0, 1)
        temperature = round(9.0 + abs(sin(latitude * 0.08)) * 18.0, 1)
        cloud_cover = round(18.0 + seed * 68.0, 1)
        precipitation = round(max(0.0, (cloud_cover - 58.0) / 28.0), 2)
        recommended_weather = "clear"
        label = "Clear"
        if wind_speed >= 30.0:
            recommended_weather = "storm"
            label = "Strong wind"
        elif precipitation >= 1.0:
            recommended_weather = "rain"
            label = "Showers"
        elif wind_speed >= 18.0:
            recommended_weather = "windy"
            label = "Moderate wind"
        return {
            "source": "fallback_weather",
            "provider": "deterministic_fallback",
            "recommended_weather": recommended_weather,
            "condition_label": label,
            "temperature_c": temperature,
            "wind_speed_kph": wind_speed,
            "precipitation_mm": precipitation,
            "cloud_cover_pct": cloud_cover,
            "visibility_label": "Reduced" if precipitation >= 1.0 else "Good",
            "operator_summary": (
                f"Live weather was unavailable, so a local fallback estimate suggests {label.lower()} conditions."
            ),
            "fallback_note": "Live weather could not be fetched. Review and override if local conditions differ.",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
