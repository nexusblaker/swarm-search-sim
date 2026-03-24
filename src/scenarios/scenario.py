"""Scenario configuration models for the swarm search simulator."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
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
    target_start_radius: int = 3
    target_spread_sigma: float = 5.0
    target_move_probability: float = 0.35
    target_speed: int = 1
    target_behavior: str = "terrain_biased_random_walk"
    probability_diffusion: float = 0.08
    negative_search_suppression: float = 0.2
    false_positive_rate: float = 0.02
    false_negative_rate: float = 0.08
    communication_radius: float = 12.0
    packet_loss_probability: float = 0.05
    communication_latency: int = 1
    coordination_mode: str = "centralized"
    base_position: Position = (0, 0)
    return_to_base_threshold: float = 28.0
    scenario_family: str = "mixed_terrain"
    save_frames: bool = True
    frame_stride: int = 3
    benchmark_num_seeds: int = 30
    experiment_num_seeds: int = 4
    benchmark_strategies: list[str] = field(
        default_factory=lambda: [
            "random_sweep",
            "sector_search",
            "probability_greedy",
            "auction_based",
            "information_gain",
        ]
    )
    benchmark_target_behaviors: list[str] = field(
        default_factory=lambda: ["terrain_biased", "stationary_intervals"]
    )
    benchmark_coordination_modes: list[str] = field(
        default_factory=lambda: ["centralized", "decentralized"]
    )
    benchmark_drone_counts: list[int] = field(default_factory=lambda: [4])
    benchmark_scenario_families: list[str] = field(
        default_factory=lambda: ["open_terrain", "poor_comms", "low_battery_budget"]
    )
    benchmark_output_dir: str = "outputs"
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
        render_data = scenario_data.get("render", {})
        sensor_data = scenario_data.get("sensor", {})
        communication_data = scenario_data.get("communication", {})
        battery_data = scenario_data.get("battery_policy", {})
        benchmark_data = scenario_data.get("benchmark", {})

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
            target_start_radius=int(scenario_data.get("target_start_radius", 3)),
            target_spread_sigma=float(
                target_assumptions.get(
                    "drift_sigma",
                    scenario_data.get("target_spread_sigma", 5.0),
                )
            ),
            target_move_probability=target_move_probability,
            target_speed=int(
                target_assumptions.get(
                    "target_speed",
                    scenario_data.get("target_speed", 1),
                )
            ),
            target_behavior=str(
                target_assumptions.get(
                    "behavior",
                    scenario_data.get("target_behavior", "terrain_biased_random_walk"),
                )
            ),
            probability_diffusion=float(scenario_data.get("probability_diffusion", 0.08)),
            negative_search_suppression=float(
                scenario_data.get("negative_search_suppression", 0.2)
            ),
            false_positive_rate=float(sensor_data.get("false_positive_rate", 0.02)),
            false_negative_rate=float(sensor_data.get("false_negative_rate", 0.08)),
            communication_radius=float(communication_data.get("radius", 12.0)),
            packet_loss_probability=float(
                communication_data.get("packet_loss_probability", 0.05)
            ),
            communication_latency=int(communication_data.get("latency", 1)),
            coordination_mode=str(
                communication_data.get("coordination_mode", "centralized")
            ),
            base_position=tuple(
                scenario_data.get(
                    "base_position",
                    communication_data.get("base_position", [0, 0]),
                )
            ),
            return_to_base_threshold=float(
                battery_data.get("return_threshold", 28.0)
            ),
            scenario_family=str(scenario_data.get("scenario_family", "mixed_terrain")),
            save_frames=bool(render_data.get("save_frames", True)),
            frame_stride=int(render_data.get("frame_stride", 3)),
            benchmark_num_seeds=int(benchmark_data.get("num_seeds", 30)),
            experiment_num_seeds=int(benchmark_data.get("experiment_num_seeds", 4)),
            benchmark_strategies=list(
                benchmark_data.get(
                    "strategies",
                    [
                        "random_sweep",
                        "sector_search",
                        "probability_greedy",
                        "auction_based",
                        "information_gain",
                    ],
                )
            ),
            benchmark_target_behaviors=list(
                benchmark_data.get(
                    "target_behaviors",
                    ["terrain_biased", "stationary_intervals"],
                )
            ),
            benchmark_coordination_modes=list(
                benchmark_data.get(
                    "coordination_modes",
                    ["centralized", "decentralized"],
                )
            ),
            benchmark_drone_counts=list(
                benchmark_data.get("drone_counts", [4])
            ),
            benchmark_scenario_families=list(
                benchmark_data.get(
                    "scenario_families",
                    ["open_terrain", "poor_comms", "low_battery_budget"],
                )
            ),
            benchmark_output_dir=str(benchmark_data.get("output_dir", "outputs")),
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

    def with_scenario_family(self, family: str) -> "ScenarioConfig":
        """Return a copy of the config with a scenario-family preset applied."""

        presets: dict[str, dict[str, Any]] = {
            "open_terrain": {
                "terrain_distribution": {
                    "plain": 0.7,
                    "forest": 0.1,
                    "hill": 0.08,
                    "urban": 0.08,
                    "water": 0.04,
                },
                "obstacle_ratio": 0.03,
                "weather": "clear",
            },
            "dense_forest": {
                "terrain_distribution": {
                    "plain": 0.18,
                    "forest": 0.55,
                    "hill": 0.12,
                    "urban": 0.07,
                    "water": 0.08,
                },
                "obstacle_ratio": 0.1,
                "weather": "windy",
            },
            "mixed_terrain": {
                "terrain_distribution": {
                    "plain": 0.4,
                    "forest": 0.24,
                    "hill": 0.16,
                    "urban": 0.14,
                    "water": 0.06,
                },
                "obstacle_ratio": 0.08,
            },
            "obstacle_heavy": {
                "obstacle_ratio": 0.16,
            },
            "poor_comms": {
                "communication_radius": 7.0,
                "packet_loss_probability": 0.35,
                "communication_latency": 3,
                "coordination_mode": "decentralized",
            },
            "high_wind": {
                "weather": "storm",
            },
            "low_battery_budget": {
                "drone_battery": 85.0,
                "return_to_base_threshold": 32.0,
            },
        }
        return replace(self, scenario_family=family, **presets.get(family, {}))
