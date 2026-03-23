"""Simulation metrics models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SimulationMetrics:
    """Summary metrics for a completed or in-progress mission."""

    time_to_detection: int | None = None
    area_covered_pct: float = 0.0
    probability_mass_covered: float = 0.0
    overlap_ratio: float = 0.0
    battery_used: float = 0.0
    mission_success: bool = False
