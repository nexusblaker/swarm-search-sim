"""Asset-package helpers for product-layer mission intake and recommendation logic."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


SENSOR_LEVEL_SCORES = {
    "basic": 0.92,
    "standard": 1.0,
    "enhanced": 1.12,
    "advanced": 1.26,
}

THERMAL_LEVEL_SCORES = {
    "none": 0.8,
    "assisted": 1.0,
    "full": 1.18,
}


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _normalize_profile(raw: dict[str, Any], index: int) -> dict[str, Any]:
    display_name = _safe_text(
        raw.get("display_name") or raw.get("model_name"),
        default=f"Drone type {index}",
    )
    sensor_level = _safe_text(raw.get("sensor_capability_level"), default="standard").lower()
    thermal_level = _safe_text(raw.get("thermal_capability_level"), default="assisted").lower()
    detection_proxy = _to_float(
        raw.get("detection_capability_proxy") or raw.get("detection_capability"),
        SENSOR_LEVEL_SCORES.get(sensor_level, 1.0) * THERMAL_LEVEL_SCORES.get(thermal_level, 1.0),
    )
    return {
        "display_name": display_name,
        "model_name": _safe_text(raw.get("model_name"), default=display_name),
        "count": max(1, _to_int(raw.get("count"), 1)),
        "max_endurance_minutes": max(20.0, _to_float(raw.get("max_endurance_minutes"), 120.0)),
        "estimated_max_range_km": max(1.0, _to_float(raw.get("estimated_max_range_km"), 12.0)),
        "cruise_speed_kph": max(10.0, _to_float(raw.get("cruise_speed_kph"), 38.0)),
        "sensor_capability_level": sensor_level if sensor_level in SENSOR_LEVEL_SCORES else "standard",
        "thermal_capability_level": thermal_level if thermal_level in THERMAL_LEVEL_SCORES else "assisted",
        "detection_capability_proxy": max(0.65, detection_proxy),
        "turnaround_time_minutes": max(5.0, _to_float(raw.get("turnaround_time_minutes"), 18.0)),
        "notes": _safe_text(raw.get("notes")),
    }


def summarize_asset_package(
    raw_package: dict[str, Any] | None,
    *,
    fallback_num_drones: int | None = None,
    fallback_drone: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a normalized, operator-facing asset package summary."""

    raw_package = dict(raw_package or {})
    drone_types_raw = raw_package.get("drone_types") or raw_package.get("profiles") or []
    drone_types = [
        _normalize_profile(item, index)
        for index, item in enumerate(drone_types_raw, start=1)
        if isinstance(item, dict)
    ]

    if not drone_types and fallback_num_drones:
        fallback_drone = dict(fallback_drone or {})
        drone_types = [
            _normalize_profile(
                {
                    "display_name": fallback_drone.get("display_name") or "General purpose drone",
                    "count": fallback_num_drones,
                    "max_endurance_minutes": fallback_drone.get("battery", 120.0),
                    "estimated_max_range_km": fallback_drone.get("estimated_max_range_km", 14.0),
                    "cruise_speed_kph": fallback_drone.get("speed_kph", 36.0),
                    "sensor_capability_level": fallback_drone.get("sensor_capability_level", "standard"),
                    "thermal_capability_level": fallback_drone.get("thermal_capability_level", "assisted"),
                    "detection_capability_proxy": fallback_drone.get("detection_capability_proxy", 1.0),
                    "turnaround_time_minutes": fallback_drone.get("turnaround_time_minutes", 18.0),
                },
                1,
            )
        ]

    total_drones = sum(item["count"] for item in drone_types)
    weighted_divisor = max(total_drones, 1)

    def weighted_mean(field: str) -> float:
        if not drone_types:
            return 0.0
        return sum(float(item[field]) * item["count"] for item in drone_types) / weighted_divisor

    sensor_score = sum(
        SENSOR_LEVEL_SCORES[item["sensor_capability_level"]] * item["count"] for item in drone_types
    ) / weighted_divisor if drone_types else 1.0
    thermal_score = sum(
        THERMAL_LEVEL_SCORES[item["thermal_capability_level"]] * item["count"] for item in drone_types
    ) / weighted_divisor if drone_types else 1.0
    detection_score = weighted_mean("detection_capability_proxy") or 1.0
    aggregate_endurance = weighted_mean("max_endurance_minutes") or 120.0
    aggregate_range = weighted_mean("estimated_max_range_km") or 12.0
    aggregate_speed = weighted_mean("cruise_speed_kph") or 36.0
    turnaround_minutes = weighted_mean("turnaround_time_minutes") or 18.0

    coverage_score = min(1.45, 0.65 + (aggregate_range / 14.0) + (aggregate_speed / 95.0))
    endurance_score = min(1.5, aggregate_endurance / 100.0)
    complexity_penalty = 0.12 if len(drone_types) > 1 else 0.0
    mix_label = "mixed" if len(drone_types) > 1 else "uniform"

    return {
        "package_name": _safe_text(raw_package.get("package_name")),
        "uniform_fleet": bool(raw_package.get("uniform_fleet", len(drone_types) <= 1)),
        "staging_location": _safe_text(raw_package.get("staging_location")),
        "notes": _safe_text(raw_package.get("notes")),
        "drone_types": drone_types,
        "fleet_composition": {
            "mix_type": mix_label,
            "total_drones": total_drones,
            "drone_type_count": len(drone_types),
            "aggregate_endurance_minutes": round(aggregate_endurance, 1),
            "aggregate_range_km": round(aggregate_range, 1),
            "aggregate_speed_kph": round(aggregate_speed, 1),
            "sensor_score": round(sensor_score, 2),
            "thermal_score": round(thermal_score, 2),
            "detection_score": round(detection_score, 2),
            "endurance_score": round(endurance_score, 2),
            "coverage_score": round(coverage_score, 2),
            "coordination_complexity": "moderate" if complexity_penalty > 0 else "low",
            "average_turnaround_minutes": round(turnaround_minutes, 1),
        },
        "operator_summary": _asset_operator_summary(drone_types, total_drones, mix_label, raw_package.get("staging_location")),
    }


def _asset_operator_summary(
    drone_types: list[dict[str, Any]],
    total_drones: int,
    mix_label: str,
    staging_location: Any,
) -> str:
    if not drone_types:
        return "No fleet package has been defined yet."

    lead = drone_types[0]["display_name"]
    fleet_text = f"{total_drones} {mix_label}-fleet drones"
    if len(drone_types) == 1:
        fleet_text = f"{total_drones} {lead}"
    staging_text = ""
    if staging_location:
        staging_text = f" staged from {staging_location}"
    if len(drone_types) == 1:
        return f"{fleet_text}{staging_text} available for this mission."
    return f"{fleet_text}{staging_text}, led by {lead} and {len(drone_types) - 1} additional asset type(s)."


def apply_asset_package_to_payload(payload: dict[str, Any], asset_package: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Attach normalized asset-package data to a scenario payload and derive simulator-friendly fields."""

    updated = deepcopy(payload)
    scenario_block = updated.setdefault("scenario", {})
    normalized = summarize_asset_package(
        asset_package,
        fallback_num_drones=_to_int(scenario_block.get("num_drones"), 0) or None,
        fallback_drone=scenario_block.get("drone"),
    )

    total_drones = normalized["fleet_composition"]["total_drones"]
    average_endurance = normalized["fleet_composition"]["aggregate_endurance_minutes"]
    average_speed = normalized["fleet_composition"]["aggregate_speed_kph"]
    coverage_score = normalized["fleet_composition"]["coverage_score"]
    sensor_score = normalized["fleet_composition"]["sensor_score"]
    thermal_score = normalized["fleet_composition"]["thermal_score"]

    if total_drones:
        scenario_block["num_drones"] = total_drones

    scenario_block["asset_package"] = normalized
    drone_block = scenario_block.setdefault("drone", {})
    drone_block.update(
        {
            "battery": round(max(60.0, average_endurance), 1),
            "speed": max(1, min(3, round(average_speed / 32.0))),
            "sensor_range": round(max(3.5, min(8.5, 2.8 + sensor_score + thermal_score + (coverage_score * 0.35))), 2),
            "fov": 130.0 if normalized["fleet_composition"]["drone_type_count"] <= 1 else 124.0,
            "estimated_max_range_km": normalized["fleet_composition"]["aggregate_range_km"],
            "cruise_speed_kph": normalized["fleet_composition"]["aggregate_speed_kph"],
            "sensor_capability_level": _safe_text(
                normalized["drone_types"][0]["sensor_capability_level"] if normalized["drone_types"] else "standard",
                default="standard",
            ),
            "thermal_capability_level": _safe_text(
                normalized["drone_types"][0]["thermal_capability_level"] if normalized["drone_types"] else "assisted",
                default="assisted",
            ),
            "turnaround_time_minutes": normalized["fleet_composition"]["average_turnaround_minutes"],
            "fleet_composition": normalized["fleet_composition"],
        }
    )
    return updated, normalized

