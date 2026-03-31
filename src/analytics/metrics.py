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
    approaching_reserve_events: int = 0
    critical_battery_events: int = 0
    recharge_cycles_started: int = 0
    recharge_cycles_completed: int = 0
    redeployments: int = 0
    rejoined_search_events: int = 0
    coverage_gap_events: int = 0
    coverage_gap_steps: int = 0
    average_active_search_drones: float = 0.0
    battery_margin_min: float = 0.0
    battery_margin_average: float = 0.0
    comms_failures: int = 0
    stale_information_events: int = 0
    path_efficiency: float = 0.0
    average_overlap_per_step: float = 0.0
    detection_under_comms_mode: str = ""
    entropy_reduction_over_time: float = 0.0
    information_gain_per_step: float = 0.0
    belief_peak_accuracy: float = 0.0
    time_to_first_candidate_detection: int | None = None
    time_to_confirmed_detection: int | None = None
    false_alarm_count: int = 0
    reroute_count: int = 0
    coordination_efficiency: float = 0.0
    return_to_base_efficiency: float = 0.0
    mission_success: bool = False
