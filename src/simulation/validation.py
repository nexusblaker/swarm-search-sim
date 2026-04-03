"""Validation, feasibility, and provenance helpers for the simulator."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha1
import json
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

from src.scenarios.scenario import ScenarioConfig
from src.simulation.calibration import MODEL_VERSION, calibration_snapshot, default_calibration_profile
from src.utils.config_loader import DEFAULT_CONFIG_PATH, load_config


BENCHMARK_CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs" / "benchmarks"
SEVERITY_ORDER = {"ready": 0, "warning": 1, "high_risk": 2, "likely_infeasible": 3}


@dataclass(slots=True)
class BenchmarkScenario:
    """One inspectable benchmark case definition."""

    benchmark_id: str
    name: str
    description: str
    purpose: str
    seed: int
    scenario_overrides: dict[str, Any] = field(default_factory=dict)
    expected_pattern: str | None = None
    expected_feasibility: str | None = None
    tolerances: dict[str, list[float]] = field(default_factory=dict)
    assumptions: list[str] = field(default_factory=list)
    model_version: str = MODEL_VERSION

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


def _deep_merge(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_benchmark_library(root: str | Path = BENCHMARK_CONFIG_DIR) -> list[BenchmarkScenario]:
    """Load the benchmark scenario library from YAML definitions."""

    root_path = Path(root)
    definitions: list[BenchmarkScenario] = []
    for path in sorted(root_path.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        definitions.append(
            BenchmarkScenario(
                benchmark_id=str(payload["id"]),
                name=str(payload["name"]),
                description=str(payload["description"]),
                purpose=str(payload["purpose"]),
                seed=int(payload.get("seed", 7)),
                scenario_overrides=dict(payload.get("scenario_overrides", {})),
                expected_pattern=payload.get("expected_pattern"),
                expected_feasibility=payload.get("expected_feasibility"),
                tolerances={
                    str(key): [float(item) for item in value]
                    for key, value in dict(payload.get("tolerances", {})).items()
                },
                assumptions=[str(item) for item in payload.get("assumptions", [])],
                model_version=str(payload.get("model_version", MODEL_VERSION)),
            )
        )
    return definitions


def build_benchmark_config(definition: BenchmarkScenario) -> ScenarioConfig:
    """Build a ScenarioConfig for the supplied benchmark definition."""

    base_payload = load_config(DEFAULT_CONFIG_PATH)
    merged = _deep_merge(base_payload, {"scenario": definition.scenario_overrides})
    merged.setdefault("scenario", {})["seed"] = definition.seed
    return ScenarioConfig.from_dict(merged)


def run_benchmark_case(definition: BenchmarkScenario) -> dict[str, Any]:
    """Run one benchmark case and validate the resulting behavior."""

    from src.simulation.engine import SimulationEngine

    config = build_benchmark_config(definition)
    engine = SimulationEngine(config)
    metrics = engine.run()
    snapshot = engine.get_state_snapshot()
    summary = {
        "metrics": asdict(metrics),
        "search_pattern": snapshot.get("search_pattern"),
        "search_pattern_label": snapshot.get("search_pattern_label"),
        "run_phase": snapshot.get("run_phase"),
        "feasibility": assess_mission_feasibility(config),
        "benchmark_context": benchmark_matches_for_config(config),
    }
    validation = validate_benchmark_result(definition, summary)
    return {
        "benchmark": definition.to_record(),
        "config": {
            "scenario_family": config.scenario_family,
            "weather": config.weather,
            "num_drones": config.num_drones,
            "reserve_preset": config.reserve_preset,
            "deployment_mode": config.deployment_mode,
        },
        "summary": summary,
        "validation": validation,
    }


def run_validation_suite(
    output_dir: str | Path | None = None,
    *,
    definitions: list[BenchmarkScenario] | None = None,
) -> dict[str, Any]:
    """Run the full benchmark validation suite and optionally persist the results."""

    library = definitions or load_benchmark_library()
    results = [run_benchmark_case(definition) for definition in library]
    passed = sum(1 for result in results if result["validation"]["passed"])
    summary = {
        "model_version": MODEL_VERSION,
        "calibration_version": calibration_snapshot()["calibration_version"],
        "benchmark_count": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }
    if output_dir is not None:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "validation_results.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
    return summary


def _band(values: list[float]) -> dict[str, float]:
    if not values:
        return {"low": 0.0, "mean": 0.0, "high": 0.0}
    ordered = sorted(float(value) for value in values)
    return {"low": ordered[0], "mean": mean(ordered), "high": ordered[-1]}


def _metric_value(run_summary: dict[str, Any], metric_name: str) -> float | None:
    metrics = run_summary.get("metrics", {})
    if metric_name in {"time_to_first_candidate_detection", "time_to_confirmed_detection", "overlap_ratio", "average_active_search_drones", "path_efficiency"}:
        value = metrics.get(metric_name)
    elif metric_name == "return_to_base_count":
        value = run_summary.get("battery_lifecycle", {}).get("return_to_base_count")
    else:
        value = metrics.get(metric_name)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate_benchmark_result(definition: BenchmarkScenario, run_summary: dict[str, Any]) -> dict[str, Any]:
    """Compare one benchmark run against the stored tolerances."""

    checks: list[dict[str, Any]] = []
    for metric_name, bounds in definition.tolerances.items():
        observed = _metric_value(run_summary, metric_name)
        low, high = bounds
        passed = observed is not None and low <= observed <= high
        checks.append(
            {
                "metric": metric_name,
                "expected_low": low,
                "expected_high": high,
                "observed": observed,
                "passed": passed,
            }
        )
    if definition.expected_pattern:
        observed_pattern = str(run_summary.get("search_pattern") or "")
        checks.append(
            {
                "metric": "search_pattern",
                "expected": definition.expected_pattern,
                "observed": observed_pattern,
                "passed": observed_pattern == definition.expected_pattern,
            }
        )
    if definition.expected_feasibility:
        observed_feasibility = str(run_summary.get("feasibility", {}).get("status") or "ready")
        checks.append(
            {
                "metric": "feasibility_status",
                "expected": definition.expected_feasibility,
                "observed": observed_feasibility,
                "passed": observed_feasibility == definition.expected_feasibility,
            }
        )
    return {
        "benchmark_id": definition.benchmark_id,
        "name": definition.name,
        "passed": all(bool(check["passed"]) for check in checks) if checks else True,
        "checks": checks,
        "purpose": definition.purpose,
        "assumptions": definition.assumptions,
        "model_version": definition.model_version,
    }


def benchmark_matches_for_config(config: ScenarioConfig) -> list[str]:
    """Return benchmark IDs that loosely match the current mission context."""

    mission_area = config.mission_area or {}
    area_sq_km = float(mission_area.get("area_sq_km", 0.0) or 0.0)
    matches: list[str] = []
    if config.last_known_status == "known" and config.scenario_family == "open_terrain":
        matches.append("small-known-lkp-open")
    if area_sq_km >= 35.0 or (config.last_known_status == "unknown" and area_sq_km >= 20.0):
        matches.append("wide-area-unknown")
    if config.scenario_family in {"dense_forest"}:
        matches.append("dense-vegetation-cue-heavy")
    if float(mission_area.get("staging_distance_to_center_km", 0.0) or 0.0) >= 4.0:
        matches.append("base-offset-stress")
    if config.turnaround_time_minutes >= 16.0 and config.num_drones <= 3:
        matches.append("battery-turnover-stress")
    if config.scenario_family in {"high_wind"} or config.weather in {"windy", "storm"}:
        matches.append("moderate-wind-steep")
    return matches


def assess_mission_feasibility(config: ScenarioConfig) -> dict[str, Any]:
    """Return deterministic pre-run feasibility warnings and summary."""

    mission_area = config.mission_area or {}
    weather_summary = mission_area.get("weather_summary", {})
    terrain_summary = mission_area.get("terrain_summary", {})
    environment_summary = mission_area.get("environment_summary", {})
    slope_summary = mission_area.get("slope_summary", {})
    area_sq_km = float(mission_area.get("area_sq_km", 0.0) or 0.0)
    resolution_m = float(mission_area.get("grid_resolution_m", mission_area.get("cell_size_m", 500.0)) or 500.0)
    grid_cols = int(mission_area.get("grid_cols") or config.map_size[0])
    grid_rows = int(mission_area.get("grid_rows") or config.map_size[1])
    grid_cells = grid_cols * grid_rows
    staging_distance = float(mission_area.get("staging_distance_to_center_km", 0.0) or 0.0)
    wind_speed = float(weather_summary.get("wind_speed_kph", 0.0) or 0.0)
    visibility = str(weather_summary.get("visibility_label", "")).lower()
    terrain_burden = str(terrain_summary.get("terrain_burden_label") or environment_summary.get("label") or "").lower()
    slope_burden = str(slope_summary.get("label") or terrain_summary.get("slope_burden") or "").lower()
    cell_width_km = resolution_m / 1000.0
    area_fallback = grid_cells * cell_width_km * cell_width_km
    if area_sq_km <= 0.0:
        area_sq_km = round(area_fallback, 2)

    reserve_factor = {"aggressive": 0.82, "balanced": 0.72, "conservative": 0.62}.get(config.reserve_preset, 0.72)
    sustained_sortie_range_km = max(config.drone_range_km * reserve_factor, 1.0)
    effective_swath_km = max(config.sensor_range * 2.0 * cell_width_km * max(1.0 - config.coverage_overlap_margin, 0.45), cell_width_km)
    coverage_capacity = max(config.num_drones * sustained_sortie_range_km * effective_swath_km, 1.0)
    coverage_pressure = area_sq_km / coverage_capacity
    issues: list[dict[str, Any]] = []

    def add_issue(severity: str, title: str, summary: str, recommendation: str) -> None:
        issues.append(
            {
                "severity": severity,
                "label": severity.replace("_", " ").title(),
                "title": title,
                "summary": summary,
                "recommendation": recommendation,
            }
        )

    if coverage_pressure >= 1.1:
        add_issue(
            "likely_infeasible",
            "Coverage pressure is very high",
            "The selected AOI is large relative to fleet endurance, sensor swath, and reserve policy. Continuous broad coverage is unlikely.",
            "Reduce the search area, move staging closer, increase fleet size, or relax reserve settings only if doctrine allows.",
        )
    elif coverage_pressure >= 0.72:
        add_issue(
            "high_risk",
            "Coverage pressure is high",
            "The area will be difficult to keep covered without rotation pressure and thinner sustained search presence.",
            "Consider a smaller AOI, more assets, or a pattern that concentrates on the highest-probability portion first.",
        )
    elif coverage_pressure >= 0.52:
        add_issue(
            "warning",
            "Coverage pressure is elevated",
            "The fleet can search this area, but continuous broad coverage may slow once drones start rotating through base.",
            "Watch active search count closely and expect some coverage thinning during return and turnaround cycles.",
        )

    transit_ratio = staging_distance / max(sustained_sortie_range_km * 0.55, 0.5)
    if transit_ratio >= 1.0:
        add_issue(
            "likely_infeasible",
            "Staging is too far from the search area",
            "Transit to the AOI consumes too much of the effective sortie range for useful search time.",
            "Move staging closer to the AOI or reduce the search area before launch.",
        )
    elif transit_ratio >= 0.72:
        add_issue(
            "high_risk",
            "Staging offset will reduce search time",
            "The current base location is far enough from the mission center that return burden will noticeably cut into on-station coverage.",
            "Consider moving staging closer or choosing a more battery-balanced search pattern.",
        )

    if wind_speed >= 34.0 or (config.weather == "storm"):
        add_issue(
            "likely_infeasible",
            "Weather burden is severe",
            "Current wind and weather conditions are likely to drive early return-to-base decisions and unstable confirmation timing.",
            "Delay launch, tighten the AOI, or move to a much more conservative plan if the mission must continue.",
        )
    elif wind_speed >= 24.0 or config.weather in {"windy", "rain"}:
        add_issue(
            "high_risk",
            "Weather increases battery burden",
            "Wind and weather are likely to reduce effective search time and increase turnover pressure.",
            "Use a higher reserve margin and expect slower time to confirmation than in calm conditions.",
        )

    if "steep" in slope_burden or ("hill" in terrain_burden and wind_speed >= 20.0):
        add_issue(
            "warning",
            "Terrain and slope will slow clean coverage",
            "Steeper ground increases route cost and makes broad, even coverage harder to sustain.",
            "Favor patterns that respect battery margin and expect more deliberate lane spacing.",
        )

    if visibility == "reduced" or any(token in terrain_burden for token in ("forest", "obstacle", "water")):
        add_issue(
            "warning",
            "Confirmation burden is elevated",
            "Terrain and visibility conditions are likely to create more cue and inspect activity before confirmation.",
            "Expect more inspection passes and give extra attention to confirmation timing in the recommendation briefing.",
        )

    if resolution_m <= 200.0 and grid_cells >= 5000:
        add_issue(
            "high_risk",
            "Grid is very fine for the selected area",
            "The chosen resolution will produce a heavy grid for this AOI and may slow simulation throughput.",
            "Increase cell size slightly or reduce the AOI if faster planning cycles matter.",
        )
    elif resolution_m >= 900.0 and config.last_known_status == "known":
        add_issue(
            "warning",
            "Grid may be too coarse for confirmation",
            "The current grid is coarse enough that cue and confirm behavior may blur together in a small known-location search.",
            "Use a finer resolution if confirmation detail is operationally important.",
        )

    if config.mission_intent == "fast_containment" and (config.reserve_preset == "conservative" or config.return_to_base_threshold >= 32.0):
        add_issue(
            "warning",
            "Reserve policy may slow containment",
            "The current reserve settings are conservative for a mission that prioritizes fast containment.",
            "Only keep these settings if safety margin is more important than initial search tempo.",
        )

    if config.turnaround_time_minutes >= 18.0 and config.num_drones <= 3 and area_sq_km >= 18.0:
        add_issue(
            "high_risk",
            "Turnaround burden is high for this fleet size",
            "Long service times and a small fleet are likely to create longer coverage gaps once return cycles begin.",
            "Add more assets, shorten turnaround assumptions, or narrow the search focus before launch.",
        )

    highest = max((SEVERITY_ORDER[issue["severity"]] for issue in issues), default=0)
    status = next(label for label, rank in SEVERITY_ORDER.items() if rank == highest)
    if not issues:
        operator_summary = "Mission looks workable under the current assumptions. Keep an eye on weather, rotation, and confirmation timing during execution."
        next_watch = "Watch the first 10 to 15 minutes for confirmation pace and battery margin."
    else:
        operator_summary = {
            "warning": "Mission is feasible, but the current setup carries operational watch items.",
            "high_risk": "Mission is possible, but the current setup carries high operational risk.",
            "likely_infeasible": "Mission is likely infeasible under the current assumptions without changing area, fleet, staging, or reserve posture.",
        }[status]
        next_watch = issues[0]["summary"]

    readiness_score = max(15, 100 - highest * 25 - len(issues) * 6)
    return {
        "status": status,
        "status_label": status.replace("_", " ").title(),
        "issue_count": len(issues),
        "readiness_score": readiness_score,
        "warnings": issues,
        "operator_summary": operator_summary,
        "next_watch": next_watch,
    }


def confidence_level_from_bands(
    success_band: dict[str, float],
    detection_band: dict[str, float],
    feasibility: dict[str, Any],
) -> dict[str, Any]:
    """Return an operator-friendly confidence level from spread and feasibility."""

    success_spread = max(success_band.get("high", 0.0) - success_band.get("low", 0.0), 0.0)
    detection_mean = max(detection_band.get("mean", 0.0), 1.0)
    detection_spread = max(detection_band.get("high", 0.0) - detection_band.get("low", 0.0), 0.0) / detection_mean
    severity = str(feasibility.get("status", "ready"))
    if severity == "likely_infeasible" or success_band.get("mean", 0.0) < 0.45:
        return {"level": "low", "label": "Low confidence", "reason": "Mission feasibility or outcome spread is weak under the current assumptions."}
    if severity == "high_risk" or success_spread > 0.3 or detection_spread > 0.8:
        return {"level": "moderate", "label": "Moderate confidence", "reason": "Results are directionally useful, but terrain, weather, or timing spread still matter."}
    return {"level": "high", "label": "High confidence", "reason": "The short evaluation bundle is reasonably consistent under the current assumptions."}


def build_run_manifest(
    config: ScenarioConfig,
    scenario_payload: dict[str, Any],
    *,
    plan_id: str | None = None,
    plan_updated_at: float | None = None,
    comparison_id: str | None = None,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    """Build a reproducible provenance manifest for one mission run."""

    calibration = calibration_snapshot(config)
    feasibility = assess_mission_feasibility(config)
    mission_area = config.mission_area or {}
    weather_summary = mission_area.get("weather_summary", {})
    terrain_summary = mission_area.get("terrain_summary", {})
    payload_fingerprint = sha1(
        json.dumps(scenario_payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:12]
    profile = default_calibration_profile()
    return {
        "seed": config.seed,
        "model_version": MODEL_VERSION,
        "scenario_version": payload_fingerprint,
        "mission_plan_version": f"{plan_id}@{plan_updated_at:.3f}" if plan_id and plan_updated_at is not None else None,
        "plan_id": plan_id,
        "comparison_id": comparison_id,
        "candidate_id": candidate_id,
        "deployment_mode": config.deployment_mode,
        "reserve_preset": config.reserve_preset,
        "search_pattern_requested": config.search_pattern,
        "mission_intent": config.mission_intent,
        "weather_source": weather_summary.get("source", config.weather),
        "aoi_source": mission_area.get("location_source", "synthetic_grid"),
        "terrain_derivation_source": terrain_summary.get("source_mode", "synthetic"),
        "calibration_version": calibration["calibration_version"],
        "calibration_snapshot": calibration["profile"],
        "units": profile.units,
        "assumptions_summary": calibration["assumptions_summary"],
        "known_limitations_summary": calibration["known_limitations_summary"],
        "benchmark_context": benchmark_matches_for_config(config),
        "feasibility_summary": feasibility,
    }
