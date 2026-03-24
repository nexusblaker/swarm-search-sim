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
    successful_returns_to_base: int = 0
    forced_low_battery_returns: int = 0
    comms_failures: int = 0
    stale_information_events: int = 0
    path_efficiency: float = 0.0
    average_overlap_per_step: float = 0.0
    detection_under_comms_mode: str = ""
    mission_success: bool = False
