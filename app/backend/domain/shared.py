"""Shared helpers for backend domain services."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.analytics.metrics import SimulationMetrics
from src.environment.mission_area import mission_area_operator_text
from src.scenarios.scenario import ScenarioConfig
from src.simulation.calibration import calibration_snapshot
from src.simulation.search_patterns import pattern_label
from src.simulation.validation import assess_mission_feasibility, benchmark_matches_for_config
from src.utils.event_logger import EventLogger


def to_jsonable(value: Any) -> Any:
    """Convert nested simulator or service state into JSON-safe values."""

    return EventLogger._sanitize(value)


def read_json(path: Path) -> Any:
    """Read a JSON file from disk."""

    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read JSONL records from disk."""

    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def read_csv_records(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    """Read CSV records into plain dictionaries."""

    dataframe = pd.read_csv(path)
    if limit is not None:
        dataframe = dataframe.head(limit)
    return dataframe.to_dict(orient="records")


def scenario_summary(config: ScenarioConfig) -> dict[str, Any]:
    """Return a compact product-facing scenario summary."""

    calibration = calibration_snapshot(config)
    return {
        "strategy": config.strategy,
        "mission_intent": config.mission_intent,
        "search_pattern": config.search_pattern,
        "search_pattern_label": pattern_label(config.search_pattern),
        "last_known_status": config.last_known_status,
        "scenario_family": config.scenario_family,
        "num_drones": config.num_drones,
        "map_size": list(config.map_size),
        "weather": config.weather,
        "target_behavior": config.target_behavior,
        "coordination_mode": config.coordination_mode,
        "deployment_mode": config.deployment_mode,
        "return_to_base_threshold": config.return_to_base_threshold,
        "reserve_preset": config.reserve_preset,
        "drone_range_km": config.drone_range_km,
        "turnaround_time_minutes": config.turnaround_time_minutes,
        "coverage_overlap_margin": config.coverage_overlap_margin,
        "mission_area": config.mission_area,
        "mission_area_summary": mission_area_operator_text(config.mission_area),
        "model_version": calibration["model_version"],
        "calibration_version": calibration["calibration_version"],
        "units": calibration["units"],
        "assumptions_summary": calibration["assumptions_summary"],
        "known_limitations_summary": calibration["known_limitations_summary"],
        "benchmark_context": benchmark_matches_for_config(config),
        "feasibility_summary": assess_mission_feasibility(config),
    }


def metrics_to_summary(metrics: SimulationMetrics) -> dict[str, Any]:
    """Return a JSON-safe metrics dictionary."""

    return to_jsonable(asdict(metrics))


def confidence_band(values: list[float]) -> dict[str, float]:
    """Return a simple mean and min/max band for lightweight uncertainty display."""

    if not values:
        return {"mean": 0.0, "low": 0.0, "high": 0.0}
    ordered = sorted(float(value) for value in values)
    return {
        "mean": float(sum(ordered) / len(ordered)),
        "low": ordered[0],
        "high": ordered[-1],
    }
