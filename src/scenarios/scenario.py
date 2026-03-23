"""Scenario configuration models for the swarm search simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Position = tuple[int, int]


@dataclass(slots=True)
class ScenarioConfig:
    """Configuration for a single swarm search-and-rescue simulation run."""

    map_size: tuple[int, int]
    weather: str
    num_drones: int
    last_known_position: Position
    target_assumptions: dict[str, Any]
    max_steps: int
    strategy: str = "probability_greedy"
    seed: int = 7
    drone_battery: float = 120.0
    drone_speed: int = 1
    sensor_range: float = 5.0
    fov: float = 120.0
    obstacle_ratio: float = 0.05
    terrain_distribution: dict[str, float] = field(
        default_factory=lambda: {
            "plain": 0.45,
            "forest": 0.2,
            "hill": 0.15,
            "urban": 0.15,
            "water": 0.05,
        }
    )
    target_initial_position: Position | None = None
    target_spread_sigma: float = 5.0
    target_move_probability: float = 0.35
    false_positive_rate: float = 0.02
    false_negative_rate: float = 0.08
    weather_modifiers: dict[str, float] = field(
        default_factory=lambda: {
            "clear": 1.0,
            "windy": 0.9,
            "rain": 0.75,
            "storm": 0.55,
        }
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScenarioConfig":
        """Build a scenario config from nested YAML-derived data."""

        scenario_data = data.get("scenario", data)
        drone_data = scenario_data.get("drone", {})
        terrain_data = scenario_data.get("terrain", {})
        sensor_data = scenario_data.get("sensor", {})

        target_assumptions = dict(scenario_data.get("target_assumptions", {}))
        target_move_probability = float(
            target_assumptions.get(
                "target_move_probability",
                scenario_data.get("target_move_probability", 0.35),
            )
        )

        return cls(
            map_size=tuple(scenario_data["map_size"]),
            weather=str(scenario_data.get("weather", "clear")),
            num_drones=int(scenario_data.get("num_drones", 1)),
            last_known_position=tuple(scenario_data["last_known_position"]),
            target_assumptions=target_assumptions,
            max_steps=int(scenario_data.get("max_steps", 50)),
            strategy=str(scenario_data.get("strategy", "probability_greedy")),
            seed=int(scenario_data.get("seed", 7)),
            drone_battery=float(drone_data.get("battery", 120.0)),
            drone_speed=int(drone_data.get("speed", 1)),
            sensor_range=float(drone_data.get("sensor_range", 5.0)),
            fov=float(drone_data.get("fov", 120.0)),
            obstacle_ratio=float(terrain_data.get("obstacle_ratio", 0.05)),
            terrain_distribution=dict(
                terrain_data.get(
                    "distribution",
                    {
                        "plain": 0.45,
                        "forest": 0.2,
                        "hill": 0.15,
                        "urban": 0.15,
                        "water": 0.05,
                    },
                )
            ),
            target_initial_position=(
                tuple(scenario_data["target_initial_position"])
                if scenario_data.get("target_initial_position") is not None
                else None
            ),
            target_spread_sigma=float(
                target_assumptions.get(
                    "drift_sigma",
                    scenario_data.get("target_spread_sigma", 5.0),
                )
            ),
            target_move_probability=target_move_probability,
            false_positive_rate=float(sensor_data.get("false_positive_rate", 0.02)),
            false_negative_rate=float(sensor_data.get("false_negative_rate", 0.08)),
            weather_modifiers=dict(
                sensor_data.get(
                    "weather_modifiers",
                    {
                        "clear": 1.0,
                        "windy": 0.9,
                        "rain": 0.75,
                        "storm": 0.55,
                    },
                )
            ),
        )
