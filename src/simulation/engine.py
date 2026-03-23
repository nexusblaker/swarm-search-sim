"""Core simulation engine for the swarm coordination simulator."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import dist
from typing import Any

import numpy as np

from src.agents.drone import Drone
from src.analytics.metrics import SimulationMetrics
from src.coordination import (
    BaseStrategy,
    ProbabilityGreedyStrategy,
    RandomSweepStrategy,
    SectorSearchStrategy,
)
from src.environment.grid import GridEnvironment
from src.probability.heatmap import ProbabilityMap
from src.scenarios.scenario import ScenarioConfig
from src.sensors.thermal import ThermalSensorModel


Position = tuple[int, int]


@dataclass(slots=True)
class TargetState:
    """Minimal moving target placeholder used in Phase 1."""

    position: Position
    move_probability: float


class SimulationEngine:
    """Coordinates environment dynamics, drone actions, sensing, and metrics."""

    def __init__(self, config: ScenarioConfig) -> None:
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self.environment: GridEnvironment | None = None
        self.drones: list[Drone] = []
        self.probability_map: ProbabilityMap | None = None
        self.sensor_model: ThermalSensorModel | None = None
        self.strategy: BaseStrategy | None = None
        self.metrics = SimulationMetrics()
        self.target: TargetState | None = None
        self.current_step = 0
        self.done = False
        self.false_positive_count = 0
        self.total_visits = 0
        self.initial_probability_values: np.ndarray | None = None
        self.unique_visited_cells: set[Position] = set()
        self.reset()

    def reset(self) -> None:
        """Reset all simulation state for a fresh run."""

        width, height = self.config.map_size
        self.rng = np.random.default_rng(self.config.seed)
        self.environment = GridEnvironment.generate(
            width=width,
            height=height,
            rng=self.rng,
            obstacle_ratio=self.config.obstacle_ratio,
            terrain_distribution=self.config.terrain_distribution,
        )
        self.drones = self._build_drones()
        self.target = TargetState(
            position=self._resolve_target_start(),
            move_probability=self.config.target_move_probability,
        )
        self.probability_map = ProbabilityMap(
            grid_shape=self.environment.shape,
            last_known_position=self._resolve_open_cell(self.config.last_known_position),
            sigma=self.config.target_spread_sigma,
        )
        self.probability_map.apply_terrain_weighting(self.environment)
        self.initial_probability_values = self.probability_map.values.copy()
        self.sensor_model = ThermalSensorModel(
            false_positive_rate=self.config.false_positive_rate,
            false_negative_rate=self.config.false_negative_rate,
            weather_modifiers=self.config.weather_modifiers,
        )
        self.strategy = self._build_strategy(self.config.strategy)
        self.strategy.reset(self.environment, self.drones)
        self.metrics = SimulationMetrics()
        self.current_step = 0
        self.done = False
        self.false_positive_count = 0
        self.total_visits = len(self.drones)
        self.unique_visited_cells = {drone.position for drone in self.drones}
        self._update_metrics()

    def step(self) -> dict[str, Any]:
        """Advance the simulation by one time step."""

        if self.done:
            return self.get_state_snapshot()

        assert self.environment is not None
        assert self.probability_map is not None
        assert self.sensor_model is not None
        assert self.strategy is not None
        assert self.target is not None

        desired_moves = self.strategy.select_moves(
            drones=self.drones,
            environment=self.environment,
            probability_map=self.probability_map,
            step_index=self.current_step,
        )

        searched_cells: set[Position] = set()
        for drone in self.drones:
            requested_move = desired_moves.get(drone.id, drone.position)
            next_position = self._resolve_step(drone.position, requested_move)
            movement_cost = self.environment.get_movement_cost(next_position)
            drone.move_to(next_position, movement_cost)
            self.total_visits += 1
            self.unique_visited_cells.add(next_position)

            scan_result = self.sensor_model.scan(
                drone=drone,
                target_position=self.target.position,
                environment=self.environment,
                weather=self.config.weather,
                rng=self.rng,
            )
            searched_cells.update(scan_result.scanned_cells)
            if scan_result.detected:
                is_true_positive = not scan_result.false_positive and dist(
                    drone.position,
                    self.target.position,
                ) <= drone.sensor_range
                drone.record_detection(
                    step=self.current_step + 1,
                    target_position=self.target.position,
                    confidence=scan_result.confidence,
                    is_true_positive=is_true_positive,
                )
                if is_true_positive and self.metrics.time_to_detection is None:
                    self.metrics.time_to_detection = self.current_step + 1
                    self.metrics.mission_success = True
                    self.done = True
                elif scan_result.false_positive:
                    self.false_positive_count += 1

        if not self.done:
            self.probability_map.update_after_negative_search(searched_cells)
            self._move_target()

        self.current_step += 1
        if self.current_step >= self.config.max_steps:
            self.done = True

        self._update_metrics()
        return self.get_state_snapshot()

    def run(self) -> SimulationMetrics:
        """Run the simulation until mission completion or max steps."""

        while not self.done:
            self.step()
        return self.metrics

    def get_state_snapshot(self) -> dict[str, Any]:
        """Return a serializable snapshot for rendering or inspection."""

        assert self.environment is not None
        assert self.probability_map is not None
        assert self.target is not None

        return {
            "step": self.current_step,
            "done": self.done,
            "weather": self.config.weather,
            "strategy": self.config.strategy,
            "terrain_grid": self.environment.terrain_grid.copy(),
            "obstacle_mask": self.environment.obstacle_mask.copy(),
            "probability_map": self.probability_map.values.copy(),
            "target_position": self.target.position,
            "visited_cells": set(self.unique_visited_cells),
            "drones": [
                {
                    "id": drone.id,
                    "position": drone.position,
                    "battery": drone.battery,
                    "visited_cells": set(drone.visited_cells),
                    "detections": list(drone.detections),
                }
                for drone in self.drones
            ],
            "metrics": asdict(self.metrics),
        }

    def _build_drones(self) -> list[Drone]:
        assert self.environment is not None

        drones: list[Drone] = []
        candidate_x_positions = np.linspace(
            0,
            self.environment.width - 1,
            num=self.config.num_drones,
            dtype=int,
        )
        for drone_id, x_position in enumerate(candidate_x_positions):
            start_position = self._resolve_open_cell((int(x_position), 0))
            drones.append(
                Drone(
                    id=drone_id,
                    position=start_position,
                    battery=self.config.drone_battery,
                    speed=self.config.drone_speed,
                    sensor_range=self.config.sensor_range,
                    fov=self.config.fov,
                )
            )
        return drones

    def _resolve_target_start(self) -> Position:
        preferred_position = (
            self.config.target_initial_position
            if self.config.target_initial_position is not None
            else self.config.last_known_position
        )
        return self._resolve_open_cell(preferred_position)

    def _resolve_open_cell(self, preferred_position: Position) -> Position:
        assert self.environment is not None

        if self.environment.in_bounds(preferred_position) and not self.environment.is_obstacle(preferred_position):
            return preferred_position

        traversable_cells = list(self.environment.iter_traversable_cells())
        return min(
            traversable_cells,
            key=lambda position: abs(position[0] - preferred_position[0]) + abs(position[1] - preferred_position[1]),
        )

    def _resolve_step(self, current: Position, requested: Position) -> Position:
        assert self.environment is not None

        if requested == current:
            return current

        cx, cy = current
        rx, ry = requested
        next_step = (
            cx + (1 if rx > cx else -1 if rx < cx else 0),
            cy + (1 if ry > cy else -1 if ry < cy else 0),
        )
        if self.environment.in_bounds(next_step) and not self.environment.is_obstacle(next_step):
            return next_step

        valid_neighbors = self.environment.get_neighbors(current, diagonal=True)
        if not valid_neighbors:
            return current
        return min(
            valid_neighbors,
            key=lambda position: abs(position[0] - requested[0]) + abs(position[1] - requested[1]),
        )

    def _move_target(self) -> None:
        assert self.environment is not None
        assert self.target is not None

        if self.rng.random() >= self.target.move_probability:
            return

        neighbors = self.environment.get_neighbors(self.target.position, diagonal=True)
        candidates = neighbors + [self.target.position]
        if not candidates:
            return

        weights = np.array(
            [1.0 / self.environment.get_movement_cost(candidate) for candidate in candidates],
            dtype=float,
        )
        weights /= weights.sum()
        chosen_index = int(self.rng.choice(len(candidates), p=weights))
        self.target.position = candidates[chosen_index]

    def _build_strategy(self, strategy_name: str) -> BaseStrategy:
        strategy_registry: dict[str, type[BaseStrategy]] = {
            RandomSweepStrategy.name: RandomSweepStrategy,
            SectorSearchStrategy.name: SectorSearchStrategy,
            ProbabilityGreedyStrategy.name: ProbabilityGreedyStrategy,
        }
        strategy_cls = strategy_registry.get(strategy_name.lower(), ProbabilityGreedyStrategy)
        return strategy_cls(rng=self.rng)

    def _update_metrics(self) -> None:
        assert self.environment is not None
        assert self.initial_probability_values is not None

        self.metrics.area_covered_pct = 100.0 * len(self.unique_visited_cells) / max(
            self.environment.traversable_cell_count,
            1,
        )
        self.metrics.probability_mass_covered = float(
            sum(self.initial_probability_values[y, x] for x, y in self.unique_visited_cells)
        )
        self.metrics.overlap_ratio = max(
            0.0,
            (self.total_visits - len(self.unique_visited_cells)) / max(self.total_visits, 1),
        )
        self.metrics.battery_used = float(sum(drone.battery_used for drone in self.drones))
