"""Core simulation engine for the swarm coordination simulator."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
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
    """Represents the moving search target."""

    position: Position
    move_probability: float
    speed: int
    behavior: str
    path_history: list[Position] = field(default_factory=list)
    detected: bool = False

    def __post_init__(self) -> None:
        self.path_history.append(self.position)

    def advance(self, environment: GridEnvironment, rng: np.random.Generator) -> None:
        """Advance the target according to its lightweight behavior model."""

        if rng.random() >= self.move_probability:
            self.path_history.append(self.position)
            return

        current_position = self.position
        for _ in range(max(self.speed, 1)):
            neighbors = environment.get_neighbors(current_position, diagonal=True)
            candidates = neighbors + [current_position]
            if not candidates:
                break

            weights = np.array(
                [
                    (1.0 / environment.get_movement_cost(candidate))
                    * (1.25 - environment.get_detection_modifier(candidate))
                    for candidate in candidates
                ],
                dtype=float,
            )
            weights = np.clip(weights, 1e-3, None)
            weights /= weights.sum()
            selected_index = int(rng.choice(len(candidates), p=weights))
            current_position = candidates[selected_index]

        self.position = current_position
        self.path_history.append(self.position)


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
        self.initial_probability_values: np.ndarray | None = None
        self.unique_visited_cells: set[Position] = set()
        self.cumulative_searched_cells: set[Position] = set()
        self.cumulative_scanned_events = 0
        self.last_searched_cells: set[Position] = set()
        self.last_detection_event: dict[str, Any] | None = None
        self.history: list[dict[str, Any]] = []
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
        self.target = self._build_target()
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
        self.unique_visited_cells = {drone.position for drone in self.drones}
        self.cumulative_searched_cells = set()
        self.cumulative_scanned_events = 0
        self.last_searched_cells = set()
        self.last_detection_event = None
        self.history = []
        self._update_metrics()
        self._record_history()

    def step(self) -> dict[str, Any]:
        """Advance the simulation by one time step."""

        if self.done:
            return self.get_state_snapshot()

        assert self.environment is not None
        assert self.probability_map is not None
        assert self.sensor_model is not None
        assert self.strategy is not None
        assert self.target is not None

        self.current_step += 1
        self.last_detection_event = None
        self.last_searched_cells = set()

        self.target.advance(self.environment, self.rng)
        self.probability_map.diffuse(
            self.environment,
            diffusion_rate=self.config.probability_diffusion,
        )

        desired_moves = self.strategy.select_moves(
            drones=self.drones,
            environment=self.environment,
            probability_map=self.probability_map,
            step_index=self.current_step,
        )

        for drone in self.drones:
            requested_move = desired_moves.get(drone.id, drone.position)
            self._move_drone(drone, requested_move)

        for drone in self.drones:
            if not drone.is_operational:
                continue

            scan_result = self.sensor_model.scan(
                drone=drone,
                target_position=self.target.position,
                environment=self.environment,
                weather=self.config.weather,
                rng=self.rng,
            )
            self.last_searched_cells.update(scan_result.scanned_cells)
            self.cumulative_searched_cells.update(scan_result.scanned_cells)
            self.cumulative_scanned_events += len(scan_result.scanned_cells)

            if scan_result.detected:
                drone.record_detection(
                    step=self.current_step,
                    target_position=self.target.position,
                    confidence=scan_result.confidence,
                    is_true_positive=scan_result.true_positive,
                )
                if scan_result.true_positive and self.last_detection_event is None:
                    self.target.detected = True
                    self.metrics.time_to_detection = self.current_step
                    self.metrics.mission_success = True
                    self.last_detection_event = {
                        "step": self.current_step,
                        "drone_id": drone.id,
                        "position": self.target.position,
                        "confidence": scan_result.confidence,
                    }
                    self.done = True
                elif scan_result.false_positive:
                    self.false_positive_count += 1

        if not self.target.detected:
            self.probability_map.update_after_negative_search(
                self.last_searched_cells,
                suppression=self.config.negative_search_suppression,
            )

        if self.current_step >= self.config.max_steps or not any(
            drone.is_operational for drone in self.drones
        ):
            self.done = True

        self._update_metrics()
        self._record_history()
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
            "target_trail": list(self.target.path_history),
            "target_detected": self.target.detected,
            "visited_cells": set(self.unique_visited_cells),
            "searched_cells": set(self.cumulative_searched_cells),
            "last_searched_cells": set(self.last_searched_cells),
            "detection_event": dict(self.last_detection_event) if self.last_detection_event else None,
            "drones": [
                {
                    "id": drone.id,
                    "position": drone.position,
                    "battery": drone.battery,
                    "visited_cells": set(drone.visited_cells),
                    "path_history": list(drone.path_history),
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
            num=max(self.config.num_drones, 1),
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

    def _build_target(self) -> TargetState:
        target_position = (
            self._resolve_open_cell(self.config.target_initial_position)
            if self.config.target_initial_position is not None
            else self._sample_target_start()
        )
        return TargetState(
            position=target_position,
            move_probability=self.config.target_move_probability,
            speed=self.config.target_speed,
            behavior=self.config.target_behavior,
        )

    def _sample_target_start(self) -> Position:
        assert self.environment is not None

        origin = self._resolve_open_cell(self.config.last_known_position)
        radius = max(self.config.target_start_radius, 0)
        candidates: list[Position] = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                candidate = (origin[0] + dx, origin[1] + dy)
                if self.environment.in_bounds(candidate) and not self.environment.is_obstacle(candidate):
                    candidates.append(candidate)
        if not candidates:
            return origin
        selected_index = int(self.rng.integers(0, len(candidates)))
        return candidates[selected_index]

    def _resolve_open_cell(self, preferred_position: Position) -> Position:
        assert self.environment is not None

        if self.environment.in_bounds(preferred_position) and not self.environment.is_obstacle(preferred_position):
            return preferred_position

        traversable_cells = list(self.environment.iter_traversable_cells())
        return min(
            traversable_cells,
            key=lambda position: abs(position[0] - preferred_position[0]) + abs(position[1] - preferred_position[1]),
        )

    def _move_drone(self, drone: Drone, requested_move: Position) -> None:
        assert self.environment is not None

        if not drone.is_operational:
            return

        current_position = drone.position
        for _ in range(max(drone.speed, 1)):
            next_position = self._resolve_step(current_position, requested_move)
            if next_position == current_position:
                break

            movement_cost = self.environment.get_movement_cost(next_position)
            if drone.battery < movement_cost:
                break

            drone.move_to(next_position, movement_cost)
            self.unique_visited_cells.add(next_position)
            current_position = next_position
            if next_position == requested_move:
                break

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

        self.metrics.area_covered_pct = 100.0 * len(self.cumulative_searched_cells) / max(
            self.environment.traversable_cell_count,
            1,
        )
        self.metrics.probability_mass_covered = float(
            sum(self.initial_probability_values[y, x] for x, y in self.cumulative_searched_cells)
        )
        self.metrics.overlap_ratio = max(
            0.0,
            (self.cumulative_scanned_events - len(self.cumulative_searched_cells))
            / max(self.cumulative_scanned_events, 1),
        )
        self.metrics.battery_used = float(sum(drone.battery_used for drone in self.drones))

    def _record_history(self) -> None:
        """Store the current state snapshot for rendering and replay."""

        self.history.append(self.get_state_snapshot())
