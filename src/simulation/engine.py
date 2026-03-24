"""Core simulation engine for the swarm coordination simulator."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from src.agents.drone import Drone
from src.analytics.metrics import SimulationMetrics
from src.coordination import (
    AuctionBasedStrategy,
    BaseStrategy,
    InformationGainStrategy,
    ProbabilityGreedyStrategy,
    RandomSweepStrategy,
    SectorSearchStrategy,
)
from src.environment.grid import GridEnvironment, TerrainType
from src.probability.heatmap import ProbabilityMap
from src.scenarios.scenario import ScenarioConfig
from src.sensors.thermal import ThermalSensorModel
from src.simulation.planning import astar_path, path_cost


Position = tuple[int, int]


@dataclass(slots=True)
class CommunicationMessage:
    sender_id: int
    recipient_id: int | None
    deliver_step: int
    payload: dict[str, Any]


@dataclass(slots=True)
class TargetState:
    position: Position
    move_probability: float
    speed: int
    behavior: str
    stationary_steps_remaining: int = 0
    path_history: list[Position] = field(default_factory=list)
    detected: bool = False

    def __post_init__(self) -> None:
        self.path_history.append(self.position)

    def advance(self, environment: GridEnvironment, rng: np.random.Generator) -> None:
        current_position = self.position
        behavior = self.behavior.lower()
        if behavior == "stationary_intervals" and self.stationary_steps_remaining > 0:
            self.stationary_steps_remaining -= 1
            self.path_history.append(current_position)
            return

        move_probability = self.move_probability * (0.45 if behavior == "injured_slow" else 1.0)
        if rng.random() >= move_probability:
            if behavior == "stationary_intervals":
                self.stationary_steps_remaining = int(rng.integers(1, 4))
            self.path_history.append(current_position)
            return

        move_speed = 1 if behavior == "injured_slow" else max(self.speed, 1)
        for _ in range(move_speed):
            neighbors = environment.get_neighbors(current_position, diagonal=True)
            candidates = neighbors + [current_position]
            if not candidates:
                break
            weights = np.array(
                [self._candidate_weight(environment, candidate, current_position) for candidate in candidates],
                dtype=float,
            )
            weights = np.clip(weights, 1e-3, None)
            weights /= weights.sum()
            current_position = candidates[int(rng.choice(len(candidates), p=weights))]

        if behavior == "stationary_intervals" and rng.random() < 0.35:
            self.stationary_steps_remaining = int(rng.integers(1, 4))

        self.position = current_position
        self.path_history.append(self.position)

    def _candidate_weight(
        self,
        environment: GridEnvironment,
        candidate: Position,
        current_position: Position,
    ) -> float:
        terrain = environment.terrain_at(candidate)
        movement_weight = 1.0 / environment.get_movement_cost(candidate)
        concealment_weight = max(1.2 - environment.get_detection_modifier(candidate), 0.2)
        if self.behavior == "random_walk":
            weight = 1.0
        elif self.behavior == "terrain_biased":
            weight = movement_weight * concealment_weight
        elif self.behavior == "trail_biased":
            weight = movement_weight * (1.4 if terrain in (TerrainType.PLAIN, TerrainType.URBAN) else 0.7)
        elif self.behavior == "injured_slow":
            weight = movement_weight * 1.1
        else:
            weight = movement_weight * concealment_weight
        if candidate == current_position:
            weight *= 0.6
        return weight


class SimulationEngine:
    """Coordinates environment dynamics, sensing, routing, comms, and metrics."""

    def __init__(self, config: ScenarioConfig) -> None:
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self.environment: GridEnvironment | None = None
        self.drones: list[Drone] = []
        self.probability_map: ProbabilityMap | None = None
        self.sensor_model: ThermalSensorModel | None = None
        self.strategy: BaseStrategy | None = None
        self.target: TargetState | None = None
        self.metrics = SimulationMetrics()
        self.current_step = 0
        self.done = False
        self.message_queue: list[CommunicationMessage] = []
        self.shared_visited_cells: set[Position] = set()
        self.shared_searched_cells: set[Position] = set()
        self.shared_intended_targets: dict[int, Position] = {}
        self.shared_search_counts: Counter[Position] = Counter()
        self.drone_search_counts: dict[int, Counter[Position]] = {}
        self.cumulative_searched_cells: set[Position] = set()
        self.cumulative_scanned_events = 0
        self.unique_visited_cells: set[Position] = set()
        self.initial_probability_values: np.ndarray | None = None
        self.last_searched_cells: set[Position] = set()
        self.last_scan_footprints: dict[int, set[Position]] = {}
        self.last_detection_event: dict[str, Any] | None = None
        self.communication_links: list[tuple[Position, Position]] = []
        self.reserved_paths: dict[int, list[Position]] = {}
        self.forced_return_events = 0
        self.successful_return_events = 0
        self.comms_failures = 0
        self.stale_information_events = 0
        self.step_overlap_history: list[float] = []
        self.total_path_cost = 0.0
        self.total_direct_cost = 0.0
        self.history: list[dict[str, Any]] = []
        self.reset()

    def reset(self) -> None:
        width, height = self.config.map_size
        self.rng = np.random.default_rng(self.config.seed)
        self.environment = GridEnvironment.generate(
            width=width,
            height=height,
            rng=self.rng,
            obstacle_ratio=self.config.obstacle_ratio,
            terrain_distribution=self.config.terrain_distribution,
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
        self.drones = self._build_drones()
        self.drone_search_counts = {drone.id: Counter() for drone in self.drones}
        self.target = self._build_target()
        self.strategy = self._build_strategy(self.config.strategy)
        self.strategy.reset(self.environment, self.drones)
        self.metrics = SimulationMetrics(detection_under_comms_mode=self.config.coordination_mode)
        self.current_step = 0
        self.done = False
        self.message_queue = []
        self.shared_visited_cells = {drone.position for drone in self.drones}
        self.shared_searched_cells = set()
        self.shared_intended_targets = {}
        self.shared_search_counts = Counter()
        self.cumulative_searched_cells = set()
        self.cumulative_scanned_events = 0
        self.unique_visited_cells = {drone.position for drone in self.drones}
        self.last_searched_cells = set()
        self.last_scan_footprints = {}
        self.last_detection_event = None
        self.communication_links = []
        self.reserved_paths = {}
        self.forced_return_events = 0
        self.successful_return_events = 0
        self.comms_failures = 0
        self.stale_information_events = 0
        self.step_overlap_history = []
        self.total_path_cost = 0.0
        self.total_direct_cost = 0.0
        self.history = []
        self._update_metrics()
        self._record_history()

    def step(self) -> dict[str, Any]:
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
        self.last_scan_footprints = {}

        self._deliver_pending_messages()
        self._refresh_communication_links()
        self._diffuse_beliefs()
        self.target.advance(self.environment, self.rng)

        for drone in self.drones:
            if self.current_step - drone.last_successful_sync_step > self.config.communication_latency:
                drone.stale_steps += 1
                self.stale_information_events += 1
            else:
                drone.stale_steps = 0

        proposed_goals = self.strategy.select_moves(
            drones=self.drones,
            environment=self.environment,
            probability_map=self.probability_map,
            step_index=self.current_step,
        )
        resolved_goals = self._apply_battery_policy(proposed_goals)
        self._plan_and_execute_routes(resolved_goals)

        step_scanned_events = 0
        step_scanned_unique: set[Position] = set()
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
            drone.searched_cells.update(scan_result.scanned_cells)
            drone.local_known_searched.update(scan_result.scanned_cells)
            self.drone_search_counts[drone.id].update(scan_result.scanned_cells)
            drone.local_probability_map = ProbabilityMap.suppress_values(
                drone.local_probability_map,
                scan_result.scanned_cells,
                self.config.negative_search_suppression,
                dict(self.drone_search_counts[drone.id]),
            )

            self.last_scan_footprints[drone.id] = set(scan_result.scanned_cells)
            self.last_searched_cells.update(scan_result.scanned_cells)
            self.cumulative_searched_cells.update(scan_result.scanned_cells)
            step_scanned_unique.update(scan_result.scanned_cells)
            step_scanned_events += len(scan_result.scanned_cells)
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

        if step_scanned_events > 0:
            self.step_overlap_history.append(
                max(0.0, (step_scanned_events - len(step_scanned_unique)) / step_scanned_events)
            )

        self._enqueue_communications()

        if self.current_step >= self.config.max_steps or not any(drone.is_operational for drone in self.drones):
            self.done = True

        self._update_metrics()
        self._record_history()
        return self.get_state_snapshot()

    def run(self) -> SimulationMetrics:
        while not self.done:
            self.step()
        return self.metrics

    def get_state_snapshot(self) -> dict[str, Any]:
        assert self.environment is not None
        assert self.probability_map is not None
        assert self.target is not None

        return {
            "step": self.current_step,
            "done": self.done,
            "weather": self.config.weather,
            "strategy": self.config.strategy,
            "coordination_mode": self.config.coordination_mode,
            "base_position": self.config.base_position,
            "terrain_grid": self.environment.terrain_grid.copy(),
            "obstacle_mask": self.environment.obstacle_mask.copy(),
            "probability_map": self.probability_map.values.copy(),
            "shared_searched_cells": set(self.shared_searched_cells),
            "target_position": self.target.position,
            "target_trail": list(self.target.path_history),
            "target_detected": self.target.detected,
            "visited_cells": set(self.unique_visited_cells),
            "searched_cells": set(self.cumulative_searched_cells),
            "last_searched_cells": set(self.last_searched_cells),
            "scan_footprints": {drone_id: set(cells) for drone_id, cells in self.last_scan_footprints.items()},
            "communication_links": list(self.communication_links),
            "reserved_paths": {drone_id: list(path) for drone_id, path in self.reserved_paths.items()},
            "returning_drones": [drone.id for drone in self.drones if drone.returning_to_base],
            "detection_event": dict(self.last_detection_event) if self.last_detection_event else None,
            "drones": [
                {
                    "id": drone.id,
                    "position": drone.position,
                    "battery": drone.battery,
                    "visited_cells": set(drone.visited_cells),
                    "path_history": list(drone.path_history),
                    "planned_path": list(drone.planned_path),
                    "intended_target": drone.intended_target,
                    "reserved_goal": drone.reserved_goal,
                    "detections": list(drone.detections),
                    "comms_online": drone.comms_online,
                    "stale_steps": drone.stale_steps,
                    "returning_to_base": drone.returning_to_base,
                }
                for drone in self.drones
            ],
            "metrics": asdict(self.metrics),
        }

    def _build_drones(self) -> list[Drone]:
        assert self.environment is not None
        assert self.probability_map is not None

        base_position = self._resolve_open_cell(self.config.base_position)
        drones: list[Drone] = []
        candidate_x_positions = np.linspace(0, self.environment.width - 1, num=max(self.config.num_drones, 1), dtype=int)
        for drone_id, x_position in enumerate(candidate_x_positions):
            start_position = self._resolve_open_cell((int(x_position), base_position[1]))
            drone = Drone(
                id=drone_id,
                position=start_position,
                battery=self.config.drone_battery,
                speed=self.config.drone_speed,
                sensor_range=self.config.sensor_range,
                fov=self.config.fov,
                base_position=base_position,
            )
            drone.local_probability_map = self.probability_map.values.copy()
            drones.append(drone)
        return drones

    def _build_target(self) -> TargetState:
        return TargetState(
            position=self._sample_target_start(),
            move_probability=self.config.target_move_probability,
            speed=self.config.target_speed,
            behavior=self.config.target_behavior,
        )

    def _sample_target_start(self) -> Position:
        assert self.environment is not None
        origin = self._resolve_open_cell(self.config.last_known_position)
        if self.config.target_initial_position is not None:
            return self._resolve_open_cell(self.config.target_initial_position)
        radius = max(self.config.target_start_radius, 0)
        candidates: list[Position] = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                candidate = (origin[0] + dx, origin[1] + dy)
                if self.environment.in_bounds(candidate) and not self.environment.is_obstacle(candidate):
                    candidates.append(candidate)
        return candidates[int(self.rng.integers(0, len(candidates)))] if candidates else origin

    def _resolve_open_cell(self, preferred_position: Position) -> Position:
        assert self.environment is not None
        if self.environment.in_bounds(preferred_position) and not self.environment.is_obstacle(preferred_position):
            return preferred_position
        traversable_cells = list(self.environment.iter_traversable_cells())
        return min(
            traversable_cells,
            key=lambda position: abs(position[0] - preferred_position[0]) + abs(position[1] - preferred_position[1]),
        )

    def _build_strategy(self, strategy_name: str) -> BaseStrategy:
        strategy_registry: dict[str, type[BaseStrategy]] = {
            RandomSweepStrategy.name: RandomSweepStrategy,
            SectorSearchStrategy.name: SectorSearchStrategy,
            ProbabilityGreedyStrategy.name: ProbabilityGreedyStrategy,
            AuctionBasedStrategy.name: AuctionBasedStrategy,
            InformationGainStrategy.name: InformationGainStrategy,
        }
        return strategy_registry.get(strategy_name.lower(), ProbabilityGreedyStrategy)(rng=self.rng)

    def _diffuse_beliefs(self) -> None:
        assert self.environment is not None
        assert self.probability_map is not None

        self.probability_map.diffuse(self.environment, diffusion_rate=self.config.probability_diffusion)
        for drone in self.drones:
            drone.local_probability_map = ProbabilityMap.diffuse_values(
                drone.local_probability_map,
                self.environment,
                self.config.probability_diffusion,
            )

    def _apply_battery_policy(self, proposed_goals: dict[int, Position]) -> dict[int, Position]:
        assert self.environment is not None

        resolved: dict[int, Position] = {}
        for drone in self.drones:
            proposed_goal = proposed_goals.get(drone.id, drone.position)
            path_home = astar_path(self.environment, drone.position, drone.base_position)
            cost_home = path_cost(self.environment, path_home)
            if drone.returning_to_base or drone.battery <= cost_home + self.config.return_to_base_threshold:
                if not drone.forced_return_triggered:
                    drone.forced_return_triggered = True
                    drone.returning_to_base = True
                    self.forced_return_events += 1
                resolved_goal = drone.base_position
            else:
                resolved_goal = proposed_goal
            drone.intended_target = resolved_goal
            resolved[drone.id] = resolved_goal
        return resolved

    def _plan_and_execute_routes(self, goals: dict[int, Position]) -> None:
        assert self.environment is not None

        self.reserved_paths = {}
        reserved_cells: set[Position] = set()
        ordered_drones = sorted(self.drones, key=lambda drone: (not drone.returning_to_base, drone.id))
        for drone in ordered_drones:
            goal = goals.get(drone.id, drone.position)
            path = astar_path(self.environment, drone.position, goal, blocked=set(reserved_cells))
            if len(path) == 1 and goal != drone.position and reserved_cells:
                path = astar_path(self.environment, drone.position, goal)
            drone.planned_path = path
            drone.reserved_goal = goal
            self.reserved_paths[drone.id] = path[: min(len(path), 6)]
            reserved_cells.update(path[1 : min(len(path), 4)])
            self.total_direct_cost += self.environment.estimate_cost(drone.position, goal)
            self.total_path_cost += path_cost(self.environment, path)

        for drone in ordered_drones:
            self._move_drone_along_path(drone)

    def _move_drone_along_path(self, drone: Drone) -> None:
        assert self.environment is not None

        if not drone.is_operational or len(drone.planned_path) <= 1:
            if drone.returning_to_base and drone.position == drone.base_position and not drone.return_completed:
                drone.return_completed = True
                self.successful_return_events += 1
            return

        steps_taken = 0
        for next_position in drone.planned_path[1:]:
            if steps_taken >= max(drone.speed, 1) or self.environment.is_obstacle(next_position):
                break
            movement_cost = self.environment.get_movement_cost(next_position)
            if drone.battery < movement_cost:
                break
            drone.move_to(next_position, movement_cost)
            self.unique_visited_cells.add(next_position)
            steps_taken += 1

        if drone.returning_to_base and drone.position == drone.base_position and not drone.return_completed:
            drone.return_completed = True
            self.successful_return_events += 1

    def _refresh_communication_links(self) -> None:
        self.communication_links = []
        for drone in self.drones:
            drone.comms_online = (
                self.current_step - drone.last_successful_sync_step
                <= self.config.communication_latency + 1
            )
        if self.config.coordination_mode == "centralized":
            for drone in self.drones:
                if self._distance(drone.position, drone.base_position) <= self.config.communication_radius:
                    self.communication_links.append((drone.position, drone.base_position))
        else:
            for index, drone_a in enumerate(self.drones):
                for drone_b in self.drones[index + 1 :]:
                    if self._distance(drone_a.position, drone_b.position) <= self.config.communication_radius:
                        self.communication_links.append((drone_a.position, drone_b.position))

    def _enqueue_communications(self) -> None:
        if self.config.coordination_mode == "centralized":
            for drone in self.drones:
                if self._distance(drone.position, drone.base_position) > self.config.communication_radius:
                    self.comms_failures += 1
                    continue
                if self.rng.random() < self.config.packet_loss_probability:
                    self.comms_failures += 1
                    continue
                self.message_queue.append(
                    CommunicationMessage(
                        sender_id=drone.id,
                        recipient_id=None,
                        deliver_step=self.current_step + self.config.communication_latency,
                        payload=self._build_drone_payload(drone),
                    )
                )
        else:
            for index, drone_a in enumerate(self.drones):
                for drone_b in self.drones[index + 1 :]:
                    if self._distance(drone_a.position, drone_b.position) > self.config.communication_radius:
                        self.comms_failures += 2
                        continue
                    for sender, recipient in ((drone_a, drone_b), (drone_b, drone_a)):
                        if self.rng.random() < self.config.packet_loss_probability:
                            self.comms_failures += 1
                            continue
                        payload = self._build_drone_payload(sender)
                        payload["sender_id"] = sender.id
                        payload["intended_targets"] = {sender.id: sender.intended_target} if sender.intended_target is not None else {}
                        self.message_queue.append(
                            CommunicationMessage(
                                sender_id=sender.id,
                                recipient_id=recipient.id,
                                deliver_step=self.current_step + self.config.communication_latency,
                                payload=payload,
                            )
                        )

    def _build_drone_payload(self, drone: Drone) -> dict[str, Any]:
        return {
            "visited_cells": set(drone.visited_cells),
            "searched_cells": set(drone.searched_cells),
            "search_counts": dict(self.drone_search_counts[drone.id]),
            "intended_target": drone.intended_target,
            "probability_map": drone.local_probability_map.copy(),
        }

    def _deliver_pending_messages(self) -> None:
        remaining: list[CommunicationMessage] = []
        for message in self.message_queue:
            if message.deliver_step > self.current_step:
                remaining.append(message)
                continue
            if message.recipient_id is None:
                self._deliver_to_hub(message)
            else:
                recipient = next(drone for drone in self.drones if drone.id == message.recipient_id)
                self._deliver_to_drone(recipient, message.payload)
        self.message_queue = remaining

    def _deliver_to_hub(self, message: CommunicationMessage) -> None:
        assert self.probability_map is not None

        sender = next(drone for drone in self.drones if drone.id == message.sender_id)
        payload = message.payload
        self.shared_visited_cells.update(payload["visited_cells"])
        self.shared_searched_cells.update(payload["searched_cells"])
        self.shared_search_counts.update(payload["search_counts"])
        if payload["intended_target"] is not None:
            self.shared_intended_targets[sender.id] = payload["intended_target"]
        self.probability_map.values = self._merge_probability_maps(
            self.probability_map.values,
            payload["probability_map"],
        )
        self.probability_map.values = ProbabilityMap.suppress_values(
            self.probability_map.values,
            self.shared_searched_cells,
            self.config.negative_search_suppression,
            dict(self.shared_search_counts),
        )
        self.probability_map.normalize()
        sender.last_successful_sync_step = self.current_step
        sender.comms_online = True
        self.message_queue.append(
            CommunicationMessage(
                sender_id=-1,
                recipient_id=sender.id,
                deliver_step=self.current_step + self.config.communication_latency,
                payload={
                    "visited_cells": set(self.shared_visited_cells),
                    "searched_cells": set(self.shared_searched_cells),
                    "intended_targets": dict(self.shared_intended_targets),
                    "probability_map": self.probability_map.values.copy(),
                },
            )
        )

    def _deliver_to_drone(self, drone: Drone, payload: dict[str, Any]) -> None:
        drone.local_known_visited.update(payload.get("visited_cells", set()))
        drone.local_known_searched.update(payload.get("searched_cells", set()))
        drone.known_teammate_targets.update(payload.get("intended_targets", {}))
        intended_target = payload.get("intended_target")
        if intended_target is not None:
            drone.known_teammate_targets[payload.get("sender_id", -1)] = intended_target
        if payload.get("probability_map") is not None:
            drone.local_probability_map = self._merge_probability_maps(
                drone.local_probability_map,
                payload["probability_map"],
            )
        drone.last_successful_sync_step = self.current_step
        drone.comms_online = True
        drone.stale_steps = 0

    @staticmethod
    def _merge_probability_maps(left: np.ndarray | None, right: np.ndarray | None) -> np.ndarray:
        if left is None and right is None:
            raise ValueError("At least one probability map must be provided.")
        merged = right.copy() if left is None else left.copy() if right is None else (left + right) / 2.0
        total = float(merged.sum())
        if total > 0.0:
            merged /= total
        return merged

    @staticmethod
    def _distance(a: Position, b: Position) -> float:
        return float(np.hypot(a[0] - b[0], a[1] - b[1]))

    def _update_metrics(self) -> None:
        assert self.environment is not None
        assert self.initial_probability_values is not None

        self.metrics.area_covered_pct = 100.0 * len(self.cumulative_searched_cells) / max(self.environment.traversable_cell_count, 1)
        self.metrics.probability_mass_covered = float(
            sum(self.initial_probability_values[y, x] for x, y in self.cumulative_searched_cells)
        )
        self.metrics.overlap_ratio = max(
            0.0,
            (self.cumulative_scanned_events - len(self.cumulative_searched_cells)) / max(self.cumulative_scanned_events, 1),
        )
        self.metrics.battery_used = float(sum(drone.battery_used for drone in self.drones))
        self.metrics.successful_returns_to_base = self.successful_return_events
        self.metrics.forced_low_battery_returns = self.forced_return_events
        self.metrics.comms_failures = self.comms_failures
        self.metrics.stale_information_events = self.stale_information_events
        self.metrics.path_efficiency = self.total_direct_cost / self.total_path_cost if self.total_path_cost > 0 else 1.0
        self.metrics.average_overlap_per_step = float(np.mean(self.step_overlap_history)) if self.step_overlap_history else 0.0
        self.metrics.detection_under_comms_mode = self.config.coordination_mode

    def _record_history(self) -> None:
        self.history.append(self.get_state_snapshot())
