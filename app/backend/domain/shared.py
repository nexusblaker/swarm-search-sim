"""Shared helpers for backend domain services."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.analytics.metrics import SimulationMetrics
from src.scenarios.scenario import ScenarioConfig
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

    return {
        "strategy": config.strategy,
        "scenario_family": config.scenario_family,
        "num_drones": config.num_drones,
        "map_size": list(config.map_size),
        "weather": config.weather,
        "target_behavior": config.target_behavior,
        "coordination_mode": config.coordination_mode,
        "return_to_base_threshold": config.return_to_base_threshold,
        "reserve_preset": config.reserve_preset,
        "drone_range_km": config.drone_range_km,
        "turnaround_time_minutes": config.turnaround_time_minutes,
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
