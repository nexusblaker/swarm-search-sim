"""Calibration and modeling-assumption helpers for the simulator."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.scenarios.scenario import ScenarioConfig


MODEL_VERSION = "slice6-operational-v1"
CALIBRATION_VERSION = "default-operational-v1"


@dataclass(slots=True)
class CalibrationProfile:
    """Documented baseline assumptions for the current model."""

    version: str = CALIBRATION_VERSION
    battery_burn_by_terrain: dict[str, float] = field(
        default_factory=lambda: {
            "plain": 1.0,
            "forest": 1.18,
            "hill": 1.24,
            "urban": 1.14,
            "water": 1.32,
        }
    )
    weather_energy_factor: dict[str, float] = field(
        default_factory=lambda: {
            "clear": 1.0,
            "windy": 1.12,
            "rain": 1.22,
            "storm": 1.38,
        }
    )
    slope_penalty_factor: float = 0.55
    cue_visibility_factor: dict[str, float] = field(
        default_factory=lambda: {
            "open": 1.0,
            "mixed": 0.88,
            "forested": 0.74,
            "obstructed": 0.66,
        }
    )
    confirm_visibility_factor: dict[str, float] = field(
        default_factory=lambda: {
            "open": 1.0,
            "mixed": 0.9,
            "forested": 0.8,
            "obstructed": 0.72,
        }
    )
    turnaround_efficiency_factor: float = 1.0
    units: dict[str, str] = field(
        default_factory=lambda: {
            "battery_energy": "sortie energy units",
            "battery_display": "percent of initial sortie energy",
            "movement_cost": "energy units per grid-to-grid move",
            "time_step": "minutes per simulation step",
            "area": "square kilometres",
            "distance": "kilometres",
            "grid_resolution": "metres per cell",
            "wind_speed": "kilometres per hour",
        }
    )
    modeled_assumptions: list[str] = field(
        default_factory=lambda: [
            "Battery is tracked in sortie energy units and converted to percent for display only.",
            "Route energy sums terrain, wind, and slope penalties over planned cell paths.",
            "Detection uses staged cue, inspect, and confirm logic rather than instant target certainty.",
            "Grid resolution and AOI size define operational scale for coverage and transit burden.",
        ]
    )
    calibrated_estimates: list[str] = field(
        default_factory=lambda: [
            "Terrain energy multipliers are tuned for relative operational burden rather than field-certified consumption.",
            "Weather and slope penalties are calibrated estimates intended to keep route costs believable and stable.",
            "Cue and confirmation visibility factors are benchmarked against scenario families, not against live sensor telemetry.",
            "Turnaround timing is treated as an operational estimate that includes swap, recharge, and basic servicing.",
        ]
    )
    known_limitations: list[str] = field(
        default_factory=lambda: [
            "The simulator is still symbolic and grid-based rather than a full aerodynamics or flight-control model.",
            "Mixed fleets influence planning, battery burden, and recommendation quality more than per-aircraft physics.",
            "Benchmarks validate reasonableness within bounded SAR-style scenarios, not all field conditions.",
            "Weather and terrain inputs are deterministic planning approximations rather than live onboard measurements.",
        ]
    )

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


def default_calibration_profile() -> CalibrationProfile:
    """Return the active default calibration profile."""

    return CalibrationProfile()


def calibration_snapshot(config: ScenarioConfig | None = None) -> dict[str, Any]:
    """Return a JSON-safe calibration snapshot for a run or recommendation."""

    profile = default_calibration_profile()
    reserve_policy = config.reserve_preset if config is not None else "balanced"
    step_duration = config.step_duration_minutes if config is not None else 3.0
    return {
        "model_version": MODEL_VERSION,
        "calibration_version": profile.version,
        "units": profile.units,
        "profile": profile.to_record(),
        "assumptions_summary": (
            f"Battery is modeled in sortie energy units with {step_duration:g}-minute steps. "
            f"Reserve logic follows the {reserve_policy.replace('_', ' ')} profile."
        ),
        "known_limitations_summary": " ".join(profile.known_limitations[:2]),
    }

