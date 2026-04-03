"""Core simulation engine for the swarm coordination simulator."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field, replace as dataclass_replace
from math import ceil
from pathlib import Path
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
from src.environment.mission_area import build_environment_from_mission_area
from src.probability.belief import BeliefState
from src.probability.heatmap import ProbabilityMap
from src.scenarios.scenario import ScenarioConfig
from src.sensors.thermal import ThermalSensorModel
from src.simulation.lifecycle import (
    BatteryDecision,
    LIFECYCLE_DEPLOYING,
    LIFECYCLE_RECHARGING,
    LIFECYCLE_READY,
    LIFECYCLE_REDEPLOYING,
    LIFECYCLE_RETURNING,
    LIFECYCLE_SEARCHING,
    LIFECYCLE_UNAVAILABLE,
    RESERVE_APPROACHING,
    RESERVE_CRITICAL,
    RESERVE_RETURNING,
    RESERVE_SAFE,
    lifecycle_label,
    reserve_status_label,
    resolve_reserve_profile,
)
from src.simulation.planning import astar_path, path_cost
from src.simulation.search_patterns import SearchPatternPlanner
from src.simulation.sensing import (
    CONTACT_CONFIRMED,
    CONTACT_CONFIRMATION_PENDING,
    CONTACT_CUE,
    CONTACT_INSPECTING,
    CONTACT_REJECTED,
    INSPECTION_CONFIRMED,
    INSPECTION_PENDING,
    INSPECTION_REJECTED,
    SENSING_CUE_DETECTED,
    SENSING_CONFIRMATION_PENDING,
    SENSING_CONFIRMED,
    SENSING_INSPECTING,
    SENSING_REJECTED,
    SENSING_RESUMED,
    SENSING_SEARCHING,
    TrackedContact,
    contact_label,
    sensing_label,
)
from src.utils.event_logger import EventLogger


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
            trail_bonus = 1.6 if environment.has_trail(candidate) else 1.0
            weight = movement_weight * trail_bonus * (1.3 if terrain in (TerrainType.PLAIN, TerrainType.URBAN) else 0.7)
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
        self.logger = EventLogger()
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
        self.approaching_reserve_events = 0
        self.critical_battery_events = 0
        self.recharge_start_events = 0
        self.recharge_complete_events = 0
        self.redeploy_events = 0
        self.rejoin_events = 0
        self.coverage_gap_events = 0
        self.coverage_gap_active = False
        self.coverage_gap_steps = 0
        self.comms_failures = 0
        self.stale_information_events = 0
        self.step_overlap_history: list[float] = []
        self.active_search_history: list[float] = []
        self.battery_margin_history: list[float] = []
        self.total_path_cost = 0.0
        self.total_direct_cost = 0.0
        self.initial_entropy = 0.0
        self.entropy_history: list[float] = []
        self.information_gain_history: list[float] = []
        self.candidate_scores: Counter[Position] = Counter()
        self.first_candidate_step: int | None = None
        self.confirmed_detection_step: int | None = None
        self.false_alarm_count = 0
        self.reroute_count = 0
        self.candidate_detection_events = 0
        self.inspection_initiated_events = 0
        self.inspection_completed_events = 0
        self.confirmed_contact_events = 0
        self.rejected_contact_events = 0
        self.contact_index = 0
        self.tracked_contacts: dict[str, TrackedContact] = {}
        self.search_pattern_planner: SearchPatternPlanner | None = None
        self.search_pattern_state: dict[str, Any] = {}
        self.global_objectives: dict[int, Position] = {}
        self.last_objectives: dict[int, Position] = {}
        self.paused = False
        self.manual_targets: dict[int, Position] = {}
        self.forced_return_overrides: set[int] = set()
        self.priority_zones: list[dict[str, Any]] = []
        self.exclusion_zones: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = []
        self.reset()

    def reset(self) -> None:
        width, height = self.config.map_size
        self.rng = np.random.default_rng(self.config.seed)
        self.environment = (
            build_environment_from_mission_area(
                self.config.mission_area,
                scenario_family=self.config.scenario_family,
                weather=self.config.weather,
            )
            if self.config.mission_area and self.config.mission_area.get("bounds")
            else GridEnvironment.load_layers(self.config.layer_paths)
            if self.config.use_external_layers and self.config.layer_paths
            else GridEnvironment.generate(
                width=width,
                height=height,
                rng=self.rng,
                obstacle_ratio=self.config.obstacle_ratio,
                terrain_distribution=self.config.terrain_distribution,
            )
        )
        self.probability_map = BeliefState(
            grid_shape=self.environment.shape,
            last_known_position=self._resolve_open_cell(self.config.last_known_position),
            sigma=self.config.target_spread_sigma,
        )
        self.probability_map.apply_terrain_weighting(self.environment)
        self.initial_probability_values = self.probability_map.values.copy()
        self.sensor_model = ThermalSensorModel(
            false_positive_rate=self.config.false_positive_rate,
            false_negative_rate=self.config.false_negative_rate,
            visual_range_factor=self.config.visual_range_factor,
            visual_false_positive_rate=self.config.visual_false_positive_rate,
            visual_false_negative_rate=self.config.visual_false_negative_rate,
            sensor_mode=self.config.sensor_mode,
            weather_modifiers=self.config.weather_modifiers,
        )
        self.drones = self._build_drones()
        self.drone_search_counts = {drone.id: Counter() for drone in self.drones}
        self.target = self._build_target()
        self.strategy = self._build_strategy(self.config.strategy)
        self.strategy.reset(self.environment, self.drones)
        self.search_pattern_planner = SearchPatternPlanner(self.config, self.environment)
        self.search_pattern_planner.prepare(self.drones)
        self.search_pattern_state = self.search_pattern_planner.state_snapshot()
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
        self.approaching_reserve_events = 0
        self.critical_battery_events = 0
        self.recharge_start_events = 0
        self.recharge_complete_events = 0
        self.redeploy_events = 0
        self.rejoin_events = 0
        self.coverage_gap_events = 0
        self.coverage_gap_active = False
        self.coverage_gap_steps = 0
        self.comms_failures = 0
        self.stale_information_events = 0
        self.step_overlap_history = []
        self.active_search_history = []
        self.battery_margin_history = []
        self.total_path_cost = 0.0
        self.total_direct_cost = 0.0
        self.initial_entropy = self.probability_map.total_entropy()
        self.entropy_history = [self.initial_entropy]
        self.information_gain_history = []
        self.candidate_scores = Counter()
        self.first_candidate_step = None
        self.confirmed_detection_step = None
        self.false_alarm_count = 0
        self.reroute_count = 0
        self.candidate_detection_events = 0
        self.inspection_initiated_events = 0
        self.inspection_completed_events = 0
        self.confirmed_contact_events = 0
        self.rejected_contact_events = 0
        self.contact_index = 0
        self.tracked_contacts = {}
        self.search_pattern_state = self.search_pattern_planner.state_snapshot() if self.search_pattern_planner else {}
        self.global_objectives = {}
        self.last_objectives = {}
        self.paused = False
        self.manual_targets = {}
        self.forced_return_overrides = set()
        self.priority_zones = []
        self.exclusion_zones = []
        self.logger = EventLogger()
        self.history = []
        if self.search_pattern_planner is not None:
            for event in self.search_pattern_planner.drain_events():
                self.logger.record(
                    str(event["event_type"]),
                    self.current_step,
                    pattern=event.get("pattern"),
                    pattern_label=event.get("pattern_label"),
                    base_pattern=event.get("base_pattern"),
                    base_pattern_label=event.get("base_pattern_label"),
                    reason=event.get("reason"),
                    summary=event.get("summary"),
                )
        self._update_metrics()
        self._record_history()

    def step(self) -> dict[str, Any]:
        if self.done or self.paused:
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
        pre_entropy = self.probability_map.total_entropy()

        self._deliver_pending_messages()
        self._refresh_communication_links()
        self._propagate_beliefs()
        self.target.advance(self.environment, self.rng)
        self._advance_lifecycle_states()

        for drone in self.drones:
            if drone.lifecycle_state in {LIFECYCLE_RECHARGING, LIFECYCLE_READY, LIFECYCLE_UNAVAILABLE}:
                drone.stale_steps = 0
                continue
            if self.current_step - drone.last_successful_sync_step > self.config.communication_latency:
                drone.stale_steps += 1
                self.stale_information_events += 1
                self.logger.record(
                    "stale_info_use",
                    self.current_step,
                    drone_id=drone.id,
                    stale_steps=drone.stale_steps,
                )
            else:
                drone.stale_steps = 0

        strategic_drones = self._strategic_drones()
        proposed_goals = self.strategy.select_moves(
            drones=strategic_drones,
            environment=self.environment,
            probability_map=self.probability_map,
            step_index=self.current_step,
        )
        if self.search_pattern_planner is not None and strategic_drones:
            pattern_goals = self.search_pattern_planner.select_goals(
                strategic_drones,
                self.probability_map,
                [
                    {
                        "id": contact.id,
                        "position": contact.position,
                        "resolved": contact.resolved,
                        "status": contact.status,
                    }
                    for contact in self.tracked_contacts.values()
                ],
                self.coverage_gap_active,
            )
            proposed_goals.update(pattern_goals)
            self.search_pattern_state = self.search_pattern_planner.state_snapshot()
            for event in self.search_pattern_planner.drain_events():
                self.logger.record(
                    str(event["event_type"]),
                    self.current_step,
                    pattern=event.get("pattern"),
                    pattern_label=event.get("pattern_label"),
                    base_pattern=event.get("base_pattern"),
                    base_pattern_label=event.get("base_pattern_label"),
                    reason=event.get("reason"),
                    summary=event.get("summary"),
                )
        proposed_goals = self._apply_operator_guidance(proposed_goals)
        proposed_goals = self._seed_redeploy_goals(proposed_goals)
        self.global_objectives = self._derive_global_objectives(proposed_goals)
        self.global_objectives = self._seed_inspection_goals(self.global_objectives)
        resolved_goals = self._apply_battery_policy(self.global_objectives)
        self._plan_and_execute_routes(resolved_goals)

        step_scanned_events = 0
        step_scanned_unique: set[Position] = set()
        for drone in self.drones:
            if not drone.can_scan:
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
            drone.local_probability_map = BeliefState.update_values(
                drone.local_probability_map,
                scanned_cells=scan_result.scanned_cells,
                positive_cells=scan_result.candidate_scores,
                suppression=self.config.negative_search_suppression,
                positive_gain=self.config.belief_positive_gain,
                search_counts=dict(self.drone_search_counts[drone.id]),
            )
            self.probability_map.update_from_observations(
                scanned_cells=scan_result.scanned_cells,
                positive_cells=scan_result.candidate_scores if drone.comms_online else None,
                suppression=self.config.negative_search_suppression,
                positive_gain=self.config.belief_positive_gain,
                search_counts=dict(self.shared_search_counts),
            )

            self.last_scan_footprints[drone.id] = set(scan_result.scanned_cells)
            self.last_searched_cells.update(scan_result.scanned_cells)
            self.cumulative_searched_cells.update(scan_result.scanned_cells)
            step_scanned_unique.update(scan_result.scanned_cells)
            step_scanned_events += len(scan_result.scanned_cells)
            self.cumulative_scanned_events += len(scan_result.scanned_cells)
            self.logger.record(
                "scan_event",
                self.current_step,
                drone_id=drone.id,
                scanned_cell_count=len(scan_result.scanned_cells),
                candidate_scores=scan_result.candidate_scores,
            )

            if scan_result.candidate_scores:
                if self.first_candidate_step is None:
                    self.first_candidate_step = self.current_step
                for candidate_position, score in scan_result.candidate_scores.items():
                    self.candidate_scores[candidate_position] += score
                    self.logger.record(
                        "detection_candidate",
                        self.current_step,
                        drone_id=drone.id,
                        position=candidate_position,
                        score=score,
                        channels=scan_result.channel_scores,
                    )

            for contact_signal in scan_result.contacts:
                self._register_contact(drone, contact_signal)

        self._resolve_contact_inspections()

        if step_scanned_events > 0:
            self.step_overlap_history.append(
                max(0.0, (step_scanned_events - len(step_scanned_unique)) / step_scanned_events)
            )
        self.information_gain_history.append(max(0.0, pre_entropy - self.probability_map.total_entropy()))
        self.entropy_history.append(self.probability_map.total_entropy())

        self._enqueue_communications()
        self._update_coverage_gap_status()

        if self.current_step >= self.config.max_steps or not self._has_future_mission_capacity():
            self.done = True

        self._update_metrics()
        self._record_history()
        return self.get_state_snapshot()

    def run(self) -> SimulationMetrics:
        while not self.done:
            self.step()
        return self.metrics

    def apply_intervention(self, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Apply an operator intervention to the active mission."""

        payload = payload or {}
        normalized_action = action.lower()
        if normalized_action == "pause":
            self.paused = True
        elif normalized_action == "resume":
            self.paused = False
        elif normalized_action == "force_return":
            drone_id = int(payload["drone_id"])
            self.forced_return_overrides.add(drone_id)
            drone = self._get_drone(drone_id)
            drone.returning_to_base = True
            drone.forced_return_triggered = True
            self._set_drone_state(drone, LIFECYCLE_RETURNING)
        elif normalized_action == "assign_waypoint":
            drone_id = int(payload["drone_id"])
            waypoint = self._normalize_position(payload.get("position") or payload["waypoint"])
            self.manual_targets[drone_id] = self._resolve_open_cell(waypoint)
        elif normalized_action == "set_priority_zone":
            self.priority_zones.append(self._normalize_zone(payload))
        elif normalized_action == "set_exclusion_zone":
            self.exclusion_zones.append(self._normalize_zone(payload))
        elif normalized_action == "switch_strategy":
            strategy_name = str(payload["strategy"])
            self.config = dataclass_replace(self.config, strategy=strategy_name)
            self.strategy = self._build_strategy(strategy_name)
            assert self.environment is not None
            self.strategy.reset(self.environment, self.drones)
        else:
            raise ValueError(f"Unsupported intervention action: {action}")

        self.logger.record(
            "operator_intervention",
            self.current_step,
            action=normalized_action,
            payload=payload,
        )
        self._record_history()
        return {
            "action": normalized_action,
            "paused": self.paused,
            "manual_targets": dict(self.manual_targets),
            "forced_return_overrides": sorted(self.forced_return_overrides),
            "priority_zones": list(self.priority_zones),
            "exclusion_zones": list(self.exclusion_zones),
            "strategy": self.config.strategy,
        }

    def get_state_snapshot(self) -> dict[str, Any]:
        assert self.environment is not None
        assert self.probability_map is not None
        assert self.target is not None

        return {
            "step": self.current_step,
            "done": self.done,
            "paused": self.paused,
            "weather": self.config.weather,
            "strategy": self.config.strategy,
            "mission_area": self.config.mission_area,
            "last_known_position": self.config.last_known_position,
            "last_known_status": self.config.last_known_status,
            "coordination_mode": self.config.coordination_mode,
            "run_phase": self._run_phase_label(),
            "base_position": self.config.base_position,
            "terrain_grid": self.environment.terrain_grid.copy(),
            "obstacle_mask": self.environment.obstacle_mask.copy(),
            "probability_map": self.probability_map.values.copy(),
            "shared_searched_cells": set(self.shared_searched_cells),
            "entropy_map": self.probability_map.entropy_map().copy(),
            "target_position": self.target.position,
            "target_trail": list(self.target.path_history),
            "target_detected": self.target.detected,
            "visited_cells": set(self.unique_visited_cells),
            "searched_cells": set(self.cumulative_searched_cells),
            "last_searched_cells": set(self.last_searched_cells),
            "scan_footprints": {drone_id: set(cells) for drone_id, cells in self.last_scan_footprints.items()},
            "communication_links": list(self.communication_links),
            "reserved_paths": {drone_id: list(path) for drone_id, path in self.reserved_paths.items()},
            "global_objectives": dict(self.global_objectives),
            **self.search_pattern_state,
            "manual_targets": dict(self.manual_targets),
            "forced_return_overrides": sorted(self.forced_return_overrides),
            "priority_zones": list(self.priority_zones),
            "exclusion_zones": list(self.exclusion_zones),
            "returning_drones": [drone.id for drone in self.drones if drone.returning_to_base],
            "active_search_drones": [drone.id for drone in self.drones if drone.contributes_to_search],
            "lifecycle_summary": self._lifecycle_summary(),
            "sensing_summary": self._sensing_summary(),
            "candidate_contacts": self._candidate_contacts_snapshot(),
            "detection_event": dict(self.last_detection_event) if self.last_detection_event else None,
            "drones": [
                {
                    "id": drone.id,
                    "position": drone.position,
                    "battery": drone.battery,
                    "battery_pct": round((drone.battery / max(drone.initial_battery, 1.0)) * 100.0, 1),
                    "visited_cells": set(drone.visited_cells),
                    "path_history": list(drone.path_history),
                    "planned_path": list(drone.planned_path),
                    "intended_target": drone.intended_target,
                    "reserved_goal": drone.reserved_goal,
                    "detections": list(drone.detections),
                    "comms_online": drone.comms_online,
                    "stale_steps": drone.stale_steps,
                    "lifecycle_state": drone.lifecycle_state,
                    "operator_status": self._operator_status(drone),
                    "sensing_state": drone.sensing_state,
                    "sensing_status": drone.sensing_status,
                    "assigned_contact_id": drone.assigned_contact_id,
                    "active_contact_position": drone.active_contact_position,
                    "reserve_status": drone.reserve_status,
                    "reserve_status_label": drone.reserve_status_label,
                    "reserve_reason": drone.reserve_reason,
                    "energy_required_to_base": drone.energy_required_to_base,
                    "reserve_required": drone.reserve_required,
                    "continue_margin_required": drone.continue_margin_required,
                    "battery_margin": drone.battery_margin,
                    "return_eta_steps": drone.return_eta_steps,
                    "return_service_eta_steps": drone.return_service_eta_steps,
                    "turnaround_remaining_steps": drone.turnaround_remaining_steps,
                    "sorties_completed": drone.sorties_completed,
                    "recharge_cycles": drone.recharge_cycles,
                    "redeployments": drone.redeployments,
                    "investigations_started": drone.investigations_started,
                    "contacts_confirmed": drone.contacts_confirmed,
                    "contacts_rejected": drone.contacts_rejected,
                    "contributing_to_search": drone.contributes_to_search,
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

    def _propagate_beliefs(self) -> None:
        assert self.environment is not None
        assert self.probability_map is not None

        self.probability_map.propagate(
            self.environment,
            target_behavior=self.config.target_behavior,
            motion_strength=self.config.belief_motion_strength,
        )
        for drone in self.drones:
            drone.local_probability_map = BeliefState.propagate_values(
                drone.local_probability_map,
                self.environment,
                target_behavior=self.config.target_behavior,
                motion_strength=self.config.belief_motion_strength,
            )

    def _derive_global_objectives(self, proposed_goals: dict[int, Position]) -> dict[int, Position]:
        """Derive high-value global objectives for hierarchical coordination."""

        if not self.config.hierarchical_planning_enabled:
            return dict(proposed_goals)

        prioritized_cells = self._priority_cells(limit=self.config.hierarchical_objective_count * 2)
        objective_candidates = BaseStrategy.top_candidate_cells(
            self.environment,
            self.probability_map,
            limit=self.config.hierarchical_objective_count,
        )
        for candidate in prioritized_cells:
            if candidate not in objective_candidates:
                objective_candidates.insert(0, candidate)
        for proposed_goal in proposed_goals.values():
            if proposed_goal not in objective_candidates:
                objective_candidates.append(proposed_goal)
        assignments: dict[int, Position] = {}
        claimed: set[Position] = set()
        for drone in self.drones:
            proposed_goal = proposed_goals.get(drone.id, drone.position)
            best_objective = proposed_goal
            best_score = float("-inf")
            for candidate in objective_candidates:
                if candidate in claimed:
                    continue
                if self._is_excluded(candidate):
                    continue
                route_cost = path_cost(
                    self.environment,
                    astar_path(self.environment, drone.position, candidate),
                )
                belief = self.probability_map.value_at(candidate)
                alignment_bonus = 5.0 if candidate == proposed_goal else -0.18 * self._distance(candidate, proposed_goal)
                priority_bonus = 3.0 if self._is_priority(candidate) else 0.0
                overlap_penalty = 1.4 if candidate in claimed else 0.0
                score = 20.0 * belief - 0.18 * route_cost + alignment_bonus + priority_bonus - overlap_penalty
                if score > best_score:
                    best_score = score
                    best_objective = candidate
            claimed.add(best_objective)
            assignments[drone.id] = best_objective
        return assignments

    def _apply_battery_policy(self, proposed_goals: dict[int, Position]) -> dict[int, Position]:
        assert self.environment is not None

        resolved: dict[int, Position] = {}
        for drone in self.drones:
            proposed_goal = proposed_goals.get(drone.id, drone.position)
            if drone.lifecycle_state == LIFECYCLE_RECHARGING:
                self._release_contact_assignment(drone)
                drone.intended_target = drone.base_position
                resolved[drone.id] = drone.base_position
                continue
            if drone.lifecycle_state == LIFECYCLE_READY:
                self._release_contact_assignment(drone)
                drone.intended_target = drone.base_position
                if drone.ready_since_step is not None and self.current_step > drone.ready_since_step and not self.done:
                    drone.redeploy_target = proposed_goal
                    drone.redeployments += 1
                    self.redeploy_events += 1
                    self._set_drone_state(
                        drone,
                        LIFECYCLE_REDEPLOYING,
                        operator_status="Redeploying",
                    )
                    self.logger.record(
                        "drone_redeployed",
                        self.current_step,
                        drone_id=drone.id,
                        target=proposed_goal,
                        reserve_preset=self.config.reserve_preset,
                    )
                else:
                    resolved[drone.id] = drone.base_position
                    continue
            if drone.lifecycle_state == LIFECYCLE_UNAVAILABLE:
                self._release_contact_assignment(drone)
                drone.intended_target = drone.position
                resolved[drone.id] = drone.position
                continue

            decision = self._evaluate_battery_decision(drone, proposed_goal)
            self._apply_reserve_status(drone, decision)

            should_return = (
                drone.id in self.forced_return_overrides
                or drone.lifecycle_state == LIFECYCLE_RETURNING
                or decision.should_return
                or decision.critical
            )

            if should_return:
                if drone.lifecycle_state != LIFECYCLE_RETURNING:
                    self._release_contact_assignment(drone)
                    self._order_return_to_base(drone, decision, proposed_goal)
                resolved_goal = drone.base_position
            else:
                if drone.lifecycle_state not in {LIFECYCLE_DEPLOYING, LIFECYCLE_REDEPLOYING} and drone.position != drone.base_position:
                    self._set_drone_state(drone, LIFECYCLE_SEARCHING)
                if not drone.assigned_contact_id and drone.sensing_state == SENSING_RESUMED:
                    self._set_drone_sensing_state(drone, SENSING_SEARCHING, clear_assignment=True)
                resolved_goal = proposed_goal
            drone.intended_target = resolved_goal
            resolved[drone.id] = resolved_goal
        return resolved

    def _seed_redeploy_goals(self, proposed_goals: dict[int, Position]) -> dict[int, Position]:
        seeded = dict(proposed_goals)
        occupied = {goal for goal in seeded.values() if goal is not None}
        for drone in self.drones:
            if drone.lifecycle_state != LIFECYCLE_READY or drone.id in seeded:
                continue
            goal = self._pick_redeploy_goal(drone, occupied)
            seeded[drone.id] = goal
            occupied.add(goal)
        return seeded

    def _pick_redeploy_goal(self, drone: Drone, occupied: set[Position]) -> Position:
        assert self.environment is not None
        assert self.probability_map is not None

        candidate_pool: list[Position] = []
        if drone.redeploy_target is not None:
            candidate_pool.append(drone.redeploy_target)
        if drone.id in self.last_objectives:
            candidate_pool.append(self.last_objectives[drone.id])
        candidate_pool.extend(self._priority_cells(limit=max(4, len(self.drones))))
        candidate_pool.extend(
            BaseStrategy.top_candidate_cells(
                self.environment,
                self.probability_map,
                limit=max(8, len(self.drones) * 3),
            )
        )

        for candidate in candidate_pool:
            if candidate == drone.base_position and len(candidate_pool) > 1:
                continue
            if candidate in occupied or self._is_excluded(candidate):
                continue
            return candidate

        fallback_cells = sorted(
            self.environment.iter_traversable_cells(),
            key=lambda position: self.probability_map.value_at(position),
            reverse=True,
        )
        for candidate in fallback_cells:
            if candidate in occupied or candidate == drone.base_position or self._is_excluded(candidate):
                continue
            return candidate
        return drone.base_position

    def _plan_and_execute_routes(self, goals: dict[int, Position]) -> None:
        assert self.environment is not None

        self.reserved_paths = {}
        reserved_cells: set[Position] = set()
        ordered_drones = sorted(self.drones, key=lambda drone: (drone.lifecycle_state != LIFECYCLE_RETURNING, drone.id))
        for drone in ordered_drones:
            goal = goals.get(drone.id, drone.position)
            previous_goal = self.last_objectives.get(drone.id)
            if previous_goal is not None and previous_goal != goal:
                self.reroute_count += 1
                self.logger.record(
                    "task_reassignment",
                    self.current_step,
                    drone_id=drone.id,
                    previous_goal=previous_goal,
                    new_goal=goal,
                )
            path = astar_path(self.environment, drone.position, goal, blocked=set(reserved_cells))
            if len(path) == 1 and goal != drone.position and reserved_cells:
                path = astar_path(self.environment, drone.position, goal)
                self.logger.record(
                    "reroute",
                    self.current_step,
                    drone_id=drone.id,
                    goal=goal,
                )
            drone.planned_path = path
            drone.reserved_goal = goal
            self.reserved_paths[drone.id] = path[: min(len(path), 6)]
            reserved_cells.update(path[1 : min(len(path), 4)])
            self.total_direct_cost += self.environment.estimate_cost(drone.position, goal)
            self.total_path_cost += path_cost(self.environment, path)
            self.last_objectives[drone.id] = goal

        for drone in ordered_drones:
            self._move_drone_along_path(drone)

    def _move_drone_along_path(self, drone: Drone) -> None:
        assert self.environment is not None

        if drone.lifecycle_state in {LIFECYCLE_RECHARGING, LIFECYCLE_READY, LIFECYCLE_UNAVAILABLE}:
            drone.planned_path = [drone.position]
            return
        if drone.position != drone.base_position:
            drone.sortie_active = True
        if not drone.is_operational or len(drone.planned_path) <= 1:
            if drone.returning_to_base and drone.position == drone.base_position and not drone.return_completed:
                self._handle_base_arrival(drone)
            return

        steps_taken = 0
        starting_state = drone.lifecycle_state
        for next_position in drone.planned_path[1:]:
            if steps_taken >= max(drone.speed, 1) or self.environment.is_obstacle(next_position):
                break
            movement_cost = self._movement_energy(next_position)
            if drone.battery < movement_cost:
                if drone.returning_to_base and drone.position != drone.base_position:
                    self._set_drone_state(drone, LIFECYCLE_UNAVAILABLE)
                    drone.reserve_reason = "Battery exhausted before reaching base."
                    self.logger.record(
                        "battery_unavailable",
                        self.current_step,
                        drone_id=drone.id,
                        position=drone.position,
                        battery=drone.battery,
                    )
                break
            drone.move_to(next_position, movement_cost)
            if drone.position != drone.base_position:
                drone.sortie_active = True
            self.unique_visited_cells.add(next_position)
            steps_taken += 1

        if drone.returning_to_base and drone.position == drone.base_position and not drone.return_completed:
            self._handle_base_arrival(drone)
            return

        if steps_taken > 0 and starting_state in {LIFECYCLE_DEPLOYING, LIFECYCLE_REDEPLOYING} and drone.position != drone.base_position:
            if starting_state == LIFECYCLE_REDEPLOYING:
                drone.rejoined_search_step = self.current_step
                self.rejoin_events += 1
                self._set_drone_state(drone, LIFECYCLE_SEARCHING, operator_status="Back in Search")
                self.logger.record(
                    "drone_rejoined_search",
                    self.current_step,
                    drone_id=drone.id,
                    position=drone.position,
                    target=drone.reserved_goal,
                )
            else:
                self._set_drone_state(drone, LIFECYCLE_SEARCHING)

    def _movement_energy(self, position: Position) -> float:
        assert self.environment is not None

        return self.environment.get_movement_cost(position) + 0.2 * self.environment.get_wind_factor(position)

    def _route_energy_cost(self, path: list[Position]) -> float:
        if len(path) <= 1:
            return 0.0
        return float(sum(self._movement_energy(position) for position in path[1:]))

    def _evaluate_battery_decision(self, drone: Drone, proposed_goal: Position) -> BatteryDecision:
        assert self.environment is not None

        profile = resolve_reserve_profile(self.config.reserve_preset)
        path_home = astar_path(self.environment, drone.position, drone.base_position)
        energy_to_base = self._route_energy_cost(path_home)
        if len(path_home) == 1 and drone.position != drone.base_position:
            energy_to_base = max(drone.initial_battery, self.config.drone_battery) * 2.0

        path_to_goal = astar_path(self.environment, drone.position, proposed_goal)
        next_position = path_to_goal[1] if len(path_to_goal) > 1 else drone.position
        projected_step_energy = 0.0 if next_position == drone.position else self._movement_energy(next_position)
        projected_home_path = astar_path(self.environment, next_position, drone.base_position)
        energy_to_base_from_next = self._route_energy_cost(projected_home_path)
        if len(projected_home_path) == 1 and next_position != drone.base_position:
            energy_to_base_from_next = max(drone.initial_battery, self.config.drone_battery) * 2.0

        reserve_floor = self.config.return_to_base_threshold * profile.floor_multiplier
        range_capacity_units = max(self.config.drone_range_km * max(self.config.drone_speed, 1) * 1.8, 1.0)
        range_pressure = min(1.0, max(energy_to_base, energy_to_base_from_next) / range_capacity_units)
        reserve_required = max(
            reserve_floor,
            max(energy_to_base, energy_to_base_from_next) * profile.contingency_ratio,
        )
        reserve_required *= 1.0 + range_pressure * profile.range_pressure_ratio
        return_required = energy_to_base + reserve_required
        continue_required = projected_step_energy + energy_to_base_from_next + reserve_required
        warning_required = continue_required + max(float(self.config.drone_speed), reserve_required * profile.warning_ratio)
        critical_required = energy_to_base + max(1.0, reserve_required * profile.critical_ratio)
        battery_margin = drone.battery - continue_required
        if drone.battery <= critical_required:
            reserve_status = RESERVE_CRITICAL
            reason = "Battery margin is critical for a safe return."
        elif drone.battery <= continue_required:
            reserve_status = RESERVE_RETURNING
            reason = "Continuing the task would cut into the safe return margin."
        elif drone.battery <= warning_required:
            reserve_status = RESERVE_APPROACHING
            reason = "Battery reserve is tightening and return planning should begin."
        else:
            reserve_status = RESERVE_SAFE
            reason = "Battery margin supports continued search."

        return BatteryDecision(
            energy_to_base=round(energy_to_base, 3),
            energy_to_base_from_next=round(energy_to_base_from_next, 3),
            reserve_required=round(reserve_required, 3),
            return_required=round(return_required, 3),
            continue_required=round(continue_required, 3),
            warning_required=round(warning_required, 3),
            critical_required=round(critical_required, 3),
            battery_margin=round(battery_margin, 3),
            return_eta_steps=max(len(path_home) - 1, 0),
            reserve_status=reserve_status,
            should_return=drone.battery <= continue_required,
            critical=drone.battery <= critical_required,
            reason=reason,
        )

    def _apply_reserve_status(self, drone: Drone, decision: BatteryDecision) -> None:
        previous_status = drone.reserve_status
        drone.reserve_status = decision.reserve_status
        drone.reserve_status_label = reserve_status_label(decision.reserve_status)
        drone.reserve_reason = decision.reason
        drone.energy_required_to_base = decision.energy_to_base
        drone.reserve_required = decision.reserve_required
        drone.continue_margin_required = decision.continue_required
        drone.battery_margin = decision.battery_margin
        drone.return_eta_steps = decision.return_eta_steps
        if drone.lifecycle_state == LIFECYCLE_RECHARGING:
            drone.return_service_eta_steps = drone.turnaround_remaining_steps
        elif drone.lifecycle_state == LIFECYCLE_RETURNING:
            drone.return_service_eta_steps = decision.return_eta_steps + self._turnaround_steps()
        else:
            drone.return_service_eta_steps = 0
        if previous_status == decision.reserve_status:
            return
        if decision.reserve_status == RESERVE_APPROACHING:
            self.approaching_reserve_events += 1
            self.logger.record(
                "approaching_reserve_limit",
                self.current_step,
                drone_id=drone.id,
                battery=drone.battery,
                energy_to_base=decision.energy_to_base,
                reserve_required=decision.reserve_required,
            )
        elif decision.reserve_status == RESERVE_CRITICAL:
            self.critical_battery_events += 1
            self.logger.record(
                "critical_battery_margin",
                self.current_step,
                drone_id=drone.id,
                battery=drone.battery,
                return_required=decision.return_required,
            )

    def _order_return_to_base(self, drone: Drone, decision: BatteryDecision, proposed_goal: Position) -> None:
        if drone.position == drone.base_position and not drone.sortie_active:
            drone.returning_to_base = False
            drone.forced_return_triggered = False
            drone.return_completed = False
            drone.return_eta_steps = 0
            drone.return_service_eta_steps = 0
            drone.reserve_reason = f"{decision.reason} Launch is being held at base."
            self._set_drone_state(drone, LIFECYCLE_DEPLOYING, operator_status="Holding at Base")
            return

        previous_state = drone.lifecycle_state
        drone.forced_return_triggered = True
        drone.returning_to_base = True
        drone.return_completed = False
        drone.ready_since_step = None
        drone.redeploy_target = None
        drone.return_service_eta_steps = decision.return_eta_steps + self._turnaround_steps()
        self.forced_return_events += 1
        self._set_drone_state(drone, LIFECYCLE_RETURNING)
        self.logger.record(
            "battery_return_ordered",
            self.current_step,
            drone_id=drone.id,
            battery=drone.battery,
            energy_to_base=decision.energy_to_base,
            reserve_required=decision.reserve_required,
            continue_required=decision.continue_required,
            previous_goal=proposed_goal,
            reserve_preset=self.config.reserve_preset,
            reason=decision.reason,
        )
        self.logger.record(
            "low_battery_return",
            self.current_step,
            drone_id=drone.id,
            battery=drone.battery,
            cost_home=decision.energy_to_base,
        )
        if previous_state in {LIFECYCLE_SEARCHING, LIFECYCLE_DEPLOYING, LIFECYCLE_REDEPLOYING}:
            self.logger.record(
                "coverage_rebalance_triggered",
                self.current_step,
                drone_id=drone.id,
                previous_goal=proposed_goal,
                active_search_drones=sum(1 for item in self.drones if item.contributes_to_search),
            )

    def _advance_lifecycle_states(self) -> None:
        for drone in self.drones:
            if drone.lifecycle_state != LIFECYCLE_RECHARGING:
                continue
            if drone.turnaround_remaining_steps > 0:
                drone.turnaround_remaining_steps -= 1
            drone.return_service_eta_steps = drone.turnaround_remaining_steps
            if drone.turnaround_remaining_steps > 0:
                continue
            drone.battery = drone.initial_battery
            drone.returning_to_base = False
            drone.forced_return_triggered = False
            drone.return_completed = False
            drone.sortie_active = False
            drone.energy_required_to_base = 0.0
            drone.reserve_required = 0.0
            drone.continue_margin_required = 0.0
            drone.battery_margin = drone.initial_battery
            drone.return_eta_steps = 0
            drone.return_service_eta_steps = 0
            drone.ready_since_step = self.current_step
            self.recharge_complete_events += 1
            self._set_drone_sensing_state(drone, SENSING_SEARCHING, clear_assignment=True)
            self._set_drone_state(drone, LIFECYCLE_READY)
            self.logger.record(
                "battery_service_completed",
                self.current_step,
                drone_id=drone.id,
                battery=drone.battery,
            )

    def _handle_base_arrival(self, drone: Drone) -> None:
        if not drone.sortie_active:
            drone.returning_to_base = False
            drone.forced_return_triggered = False
            drone.return_completed = False
            drone.return_eta_steps = 0
            drone.return_service_eta_steps = 0
            if drone.lifecycle_state == LIFECYCLE_RETURNING:
                self._set_drone_state(drone, LIFECYCLE_DEPLOYING, operator_status="Holding at Base")
            return

        self.logger.record(
            "arrived_at_base",
            self.current_step,
            drone_id=drone.id,
            battery=drone.battery,
        )
        self._start_turnaround(drone)

    def _start_turnaround(self, drone: Drone) -> None:
        drone.return_completed = True
        drone.returning_to_base = False
        drone.forced_return_triggered = False
        drone.ready_since_step = None
        drone.redeploy_target = None
        drone.sortie_active = False
        drone.sorties_completed += 1
        drone.recharge_cycles += 1
        self.successful_return_events += 1
        self.recharge_start_events += 1
        drone.turnaround_remaining_steps = self._turnaround_steps()
        drone.return_eta_steps = 0
        drone.return_service_eta_steps = drone.turnaround_remaining_steps
        self._set_drone_sensing_state(drone, SENSING_SEARCHING, clear_assignment=True)
        self._set_drone_state(drone, LIFECYCLE_RECHARGING)
        self.logger.record("return_to_base", self.current_step, drone_id=drone.id)
        self.logger.record(
            "battery_service_started",
            self.current_step,
            drone_id=drone.id,
            turnaround_steps=drone.turnaround_remaining_steps,
            turnaround_minutes=self.config.turnaround_time_minutes,
        )

    def _turnaround_steps(self) -> int:
        return max(1, int(ceil(self.config.turnaround_time_minutes / max(self.config.step_duration_minutes, 1.0))))

    def _strategic_drones(self) -> list[Drone]:
        return [
            drone
            for drone in self.drones
            if drone.lifecycle_state not in {LIFECYCLE_RETURNING, LIFECYCLE_RECHARGING, LIFECYCLE_READY, LIFECYCLE_UNAVAILABLE}
        ]

    def _set_drone_state(self, drone: Drone, lifecycle_state: str, operator_status: str | None = None) -> None:
        drone.lifecycle_state = lifecycle_state
        drone.operator_status = operator_status or lifecycle_label(lifecycle_state)
        drone.last_lifecycle_change_step = self.current_step

    def _set_drone_sensing_state(
        self,
        drone: Drone,
        sensing_state: str,
        contact: TrackedContact | None = None,
        *,
        clear_assignment: bool = False,
    ) -> None:
        drone.sensing_state = sensing_state
        drone.sensing_status = sensing_label(sensing_state)
        if contact is not None:
            drone.assigned_contact_id = contact.id
            drone.active_contact_position = contact.position
        elif clear_assignment:
            drone.assigned_contact_id = None
            drone.active_contact_position = None

    def _operator_status(self, drone: Drone) -> str:
        if drone.lifecycle_state in {
            LIFECYCLE_RETURNING,
            LIFECYCLE_RECHARGING,
            LIFECYCLE_READY,
            LIFECYCLE_UNAVAILABLE,
        }:
            return drone.operator_status
        if drone.sensing_state != SENSING_SEARCHING:
            return drone.sensing_status
        return drone.operator_status

    def _find_tracked_contact(self, position: Position, is_true_target: bool) -> TrackedContact | None:
        unresolved = [contact for contact in self.tracked_contacts.values() if not contact.resolved]
        if is_true_target:
            for contact in unresolved:
                if contact.is_true_target:
                    return contact
        for contact in unresolved:
            if self._distance(contact.position, position) <= 1.0:
                return contact
        return None

    def _register_contact(self, drone: Drone, signal: Any) -> TrackedContact:
        contact = self._find_tracked_contact(signal.position, signal.is_true_target)
        created = False
        if contact is None:
            self.contact_index += 1
            contact = TrackedContact(
                id=f"contact-{self.contact_index}",
                position=signal.position,
                status=CONTACT_CUE,
                confidence=signal.confidence,
                candidate_score=signal.candidate_score,
                cue_step=self.current_step,
                detecting_drone_id=drone.id,
                source_channels=dict(signal.source_channels),
                is_true_target=signal.is_true_target,
                false_positive=signal.false_positive,
                distance=signal.distance,
                terrain_modifier=signal.terrain_modifier,
                weather_factor=signal.weather_factor,
                note=signal.note,
                last_update_step=self.current_step,
                confidence_history=[signal.confidence],
            )
            self.tracked_contacts[contact.id] = contact
            self.candidate_detection_events += 1
            if signal.false_positive:
                self.false_alarm_count += 1
            self.logger.record(
                "possible_contact_detected",
                self.current_step,
                drone_id=drone.id,
                contact_id=contact.id,
                position=signal.position,
                confidence=round(signal.confidence, 3),
                candidate_score=round(signal.candidate_score, 3),
                requires_inspection=signal.requires_inspection,
                note=signal.note,
            )
            created = True
        else:
            contact.position = signal.position
            contact.confidence = max(contact.confidence, signal.confidence)
            contact.candidate_score += signal.candidate_score
            contact.last_update_step = self.current_step
            contact.note = signal.note
            contact.distance = signal.distance
            contact.terrain_modifier = signal.terrain_modifier
            contact.weather_factor = signal.weather_factor
            contact.source_channels = dict(signal.source_channels)
            contact.confidence_history.append(signal.confidence)

        drone.record_detection(
            step=self.current_step,
            target_position=signal.position,
            confidence=signal.confidence,
            is_true_positive=signal.is_true_target,
            stage="cue",
            outcome="candidate",
            contact_id=contact.id,
        )
        if created and drone.sensing_state == SENSING_SEARCHING and not drone.assigned_contact_id:
            self._set_drone_sensing_state(drone, SENSING_CUE_DETECTED, contact)
        return contact

    def _can_assign_inspection(self, drone: Drone) -> bool:
        return (
            drone.is_operational
            and drone.lifecycle_state not in {
                LIFECYCLE_RETURNING,
                LIFECYCLE_RECHARGING,
                LIFECYCLE_READY,
                LIFECYCLE_UNAVAILABLE,
            }
        )

    def _pick_inspector(self, contact: TrackedContact) -> Drone | None:
        assert self.environment is not None

        if contact.assigned_drone_id is not None:
            assigned = self._get_drone(contact.assigned_drone_id)
            if self._can_assign_inspection(assigned):
                return assigned

        candidates: list[tuple[float, Drone]] = []
        for drone in self.drones:
            if not self._can_assign_inspection(drone):
                continue
            if drone.assigned_contact_id and drone.assigned_contact_id != contact.id:
                continue
            route = astar_path(self.environment, drone.position, contact.position)
            route_cost = path_cost(self.environment, route)
            detecting_bonus = -1.6 if drone.id == contact.detecting_drone_id else 0.0
            candidates.append((route_cost + detecting_bonus, drone))

        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1].id))
        return candidates[0][1]

    def _assign_contact_to_drone(self, contact: TrackedContact, drone: Drone) -> None:
        if contact.assigned_drone_id == drone.id:
            state = (
                SENSING_CONFIRMATION_PENDING
                if contact.status == CONTACT_CONFIRMATION_PENDING
                else SENSING_INSPECTING
            )
            self._set_drone_sensing_state(drone, state, contact)
            return

        if contact.assigned_drone_id is not None and contact.assigned_drone_id != drone.id:
            self._release_contact_assignment(self._get_drone(contact.assigned_drone_id))

        contact.assigned_drone_id = drone.id
        contact.status = CONTACT_INSPECTING
        contact.inspect_started_step = contact.inspect_started_step or self.current_step
        contact.last_update_step = self.current_step
        drone.investigations_started += 1
        self.inspection_initiated_events += 1
        self._set_drone_sensing_state(drone, SENSING_INSPECTING, contact)
        self.logger.record(
            "inspection_initiated",
            self.current_step,
            drone_id=drone.id,
            contact_id=contact.id,
            position=contact.position,
            confidence=round(contact.confidence, 3),
            detecting_drone_id=contact.detecting_drone_id,
        )

    def _seed_inspection_goals(self, proposed_goals: dict[int, Position]) -> dict[int, Position]:
        seeded = dict(proposed_goals)
        unresolved_contacts = sorted(
            [contact for contact in self.tracked_contacts.values() if not contact.resolved],
            key=lambda contact: (
                contact.status != CONTACT_INSPECTING,
                contact.cue_step,
                -contact.confidence,
            ),
        )
        active_assignments: set[str] = set()

        for contact in unresolved_contacts:
            inspector = self._pick_inspector(contact)
            if inspector is None:
                continue
            self._assign_contact_to_drone(contact, inspector)
            seeded[inspector.id] = contact.position
            active_assignments.add(contact.id)

        for drone in self.drones:
            if drone.assigned_contact_id and drone.assigned_contact_id not in active_assignments:
                self._release_contact_assignment(drone)
            if (
                not drone.assigned_contact_id
                and drone.sensing_state in {
                    SENSING_CUE_DETECTED,
                    SENSING_CONFIRMATION_PENDING,
                    SENSING_REJECTED,
                    SENSING_RESUMED,
                }
            ):
                self._set_drone_sensing_state(drone, SENSING_SEARCHING, clear_assignment=True)
        return seeded

    def _release_contact_assignment(self, drone: Drone) -> None:
        if drone.assigned_contact_id is not None:
            contact = self.tracked_contacts.get(drone.assigned_contact_id)
            if contact is not None and not contact.resolved and contact.assigned_drone_id == drone.id:
                contact.assigned_drone_id = None
                if contact.status not in {CONTACT_CONFIRMED, CONTACT_REJECTED}:
                    contact.status = CONTACT_CUE
                    contact.last_update_step = self.current_step
        self._set_drone_sensing_state(drone, SENSING_SEARCHING, clear_assignment=True)

    def _resolve_contact_inspections(self) -> None:
        assert self.environment is not None
        assert self.sensor_model is not None

        for contact in sorted(self.tracked_contacts.values(), key=lambda item: item.cue_step):
            if contact.resolved or contact.assigned_drone_id is None:
                continue
            drone = self._get_drone(contact.assigned_drone_id)
            if not self._can_assign_inspection(drone):
                self._release_contact_assignment(drone)
                continue

            distance = self._distance(drone.position, contact.position)
            inspect_trigger_range = max(2.0, drone.sensor_range * 0.55)
            if distance > inspect_trigger_range:
                continue

            contact.inspection_attempts += 1
            outcome = self.sensor_model.inspect_contact(
                drone=drone,
                contact=contact,
                environment=self.environment,
                weather=self.config.weather,
                rng=self.rng,
            )
            self.inspection_completed_events += 1
            contact.inspect_completed_step = self.current_step
            contact.last_update_step = self.current_step
            contact.confidence = max(contact.confidence, outcome.confidence)
            contact.confidence_history.append(outcome.confidence)
            drone.record_detection(
                step=self.current_step,
                target_position=contact.position,
                confidence=outcome.confidence,
                is_true_positive=contact.is_true_target,
                stage="inspect",
                outcome=outcome.outcome,
                contact_id=contact.id,
            )
            self.logger.record(
                "inspection_pass_complete",
                self.current_step,
                drone_id=drone.id,
                contact_id=contact.id,
                position=contact.position,
                confidence=round(outcome.confidence, 3),
                outcome=outcome.outcome,
                note=outcome.note,
            )

            if outcome.outcome == INSPECTION_CONFIRMED:
                self._confirm_contact(contact, drone, outcome)
            elif outcome.outcome == INSPECTION_REJECTED:
                self._reject_contact(contact, drone, outcome)
            else:
                contact.status = CONTACT_CONFIRMATION_PENDING
                contact.outcome = INSPECTION_PENDING
                contact.note = outcome.note
                self._set_drone_sensing_state(drone, SENSING_CONFIRMATION_PENDING, contact)

    def _confirm_contact(self, contact: TrackedContact, drone: Drone, outcome: Any) -> None:
        assert self.target is not None

        contact.status = CONTACT_CONFIRMED
        contact.resolved = True
        contact.outcome = INSPECTION_CONFIRMED
        contact.resolution_step = self.current_step
        contact.note = outcome.note
        drone.contacts_confirmed += 1
        self.confirmed_contact_events += 1
        self.target.detected = True
        self.metrics.time_to_detection = self.current_step
        self.metrics.mission_success = True
        self.confirmed_detection_step = self.current_step
        self.last_detection_event = {
            "step": self.current_step,
            "drone_id": drone.id,
            "position": contact.position,
            "confidence": outcome.confidence,
            "contact_id": contact.id,
            "summary": "Target confirmed after close inspection.",
        }
        self.logger.record(
            "contact_confirmed",
            self.current_step,
            drone_id=drone.id,
            contact_id=contact.id,
            position=contact.position,
            confidence=round(outcome.confidence, 3),
            note=outcome.note,
        )
        self.logger.record(
            "confirmed_detection",
            self.current_step,
            drone_id=drone.id,
            contact_id=contact.id,
            position=contact.position,
            confidence=round(outcome.confidence, 3),
        )
        self._set_drone_sensing_state(drone, SENSING_CONFIRMED, contact)
        self.done = True

    def _reject_contact(self, contact: TrackedContact, drone: Drone, outcome: Any) -> None:
        contact.status = CONTACT_REJECTED
        contact.resolved = True
        contact.outcome = INSPECTION_REJECTED
        contact.resolution_step = self.current_step
        contact.note = outcome.note
        drone.contacts_rejected += 1
        self.rejected_contact_events += 1
        self.logger.record(
            "false_positive_rejected",
            self.current_step,
            drone_id=drone.id,
            contact_id=contact.id,
            position=contact.position,
            confidence=round(outcome.confidence, 3),
            note=outcome.note,
        )
        self.logger.record(
            "search_resumed_after_reject",
            self.current_step,
            drone_id=drone.id,
            contact_id=contact.id,
            position=contact.position,
        )
        contact.assigned_drone_id = None
        self._set_drone_sensing_state(drone, SENSING_RESUMED, clear_assignment=True)

    def _update_coverage_gap_status(self) -> None:
        active_search = sum(1 for drone in self.drones if drone.contributes_to_search)
        threshold = max(1, int(ceil(self.config.num_drones * 0.6)))
        gap_active = active_search < threshold
        if gap_active:
            self.coverage_gap_steps += 1
        if gap_active and not self.coverage_gap_active:
            self.coverage_gap_events += 1
            self.logger.record(
                "coverage_gap",
                self.current_step,
                active_search_drones=active_search,
                threshold=threshold,
            )
        if not gap_active and self.coverage_gap_active:
            self.logger.record(
                "coverage_rebalanced",
                self.current_step,
                active_search_drones=active_search,
            )
        self.coverage_gap_active = gap_active

    def _has_future_mission_capacity(self) -> bool:
        return any(
            drone.lifecycle_state in {LIFECYCLE_DEPLOYING, LIFECYCLE_SEARCHING, LIFECYCLE_RETURNING, LIFECYCLE_RECHARGING, LIFECYCLE_READY, LIFECYCLE_REDEPLOYING}
            or drone.is_operational
            for drone in self.drones
        )

    def _run_phase_label(self) -> str:
        if self.done and self.target.detected:
            return "Target confirmed"
        if self.done:
            return "Mission complete"
        if any(contact.status == CONTACT_INSPECTING for contact in self.tracked_contacts.values() if not contact.resolved):
            return "Inspecting possible contact"
        if any(
            contact.status in {CONTACT_CUE, CONTACT_CONFIRMATION_PENDING}
            for contact in self.tracked_contacts.values()
            if not contact.resolved
        ):
            return "Possible contact detected"
        if any(drone.lifecycle_state == LIFECYCLE_RECHARGING for drone in self.drones):
            return "Battery rotation underway"
        if any(drone.lifecycle_state == LIFECYCLE_RETURNING for drone in self.drones):
            return "Return-to-base rotation underway"
        if any(drone.lifecycle_state == LIFECYCLE_READY for drone in self.drones):
            return "Assets ready to redeploy"
        return "Active search"

    def _lifecycle_summary(self) -> dict[str, Any]:
        state_counts = Counter(drone.lifecycle_state for drone in self.drones)
        return {
            "run_phase": self._run_phase_label(),
            "reserve_preset": self.config.reserve_preset,
            "drone_state_counts": dict(state_counts),
            "active_search_drones": sum(1 for drone in self.drones if drone.contributes_to_search),
            "returning_drones": state_counts.get(LIFECYCLE_RETURNING, 0),
            "recharging_drones": state_counts.get(LIFECYCLE_RECHARGING, 0),
            "ready_to_redeploy": state_counts.get(LIFECYCLE_READY, 0),
            "coverage_gap_active": self.coverage_gap_active,
            "coverage_gap_steps": self.coverage_gap_steps,
        }

    def _sensing_summary(self) -> dict[str, Any]:
        unresolved = [contact for contact in self.tracked_contacts.values() if not contact.resolved]
        status_counts = Counter(contact.status for contact in unresolved)
        return {
            "candidate_detection_count": self.candidate_detection_events,
            "inspections_initiated": self.inspection_initiated_events,
            "inspections_completed": self.inspection_completed_events,
            "confirmed_contact_count": self.confirmed_contact_events,
            "rejected_contact_count": self.rejected_contact_events,
            "active_candidate_contacts": status_counts.get(CONTACT_CUE, 0),
            "contacts_under_inspection": status_counts.get(CONTACT_INSPECTING, 0),
            "confirmation_pending": status_counts.get(CONTACT_CONFIRMATION_PENDING, 0),
            "operator_summary": (
                "A possible contact is being inspected."
                if status_counts.get(CONTACT_INSPECTING, 0) > 0
                else "A possible contact is awaiting inspection."
                if status_counts.get(CONTACT_CUE, 0) > 0 or status_counts.get(CONTACT_CONFIRMATION_PENDING, 0) > 0
                else "No active contacts are awaiting confirmation."
            ),
        }

    def _candidate_contacts_snapshot(self) -> list[dict[str, Any]]:
        contacts = sorted(
            self.tracked_contacts.values(),
            key=lambda contact: (
                contact.resolved,
                -(contact.resolution_step or 0),
                -contact.cue_step,
            ),
        )
        return [
            {
                "id": contact.id,
                "position": contact.position,
                "status": contact.status,
                "status_label": contact_label(contact.status),
                "confidence": round(contact.confidence, 3),
                "candidate_score": round(contact.candidate_score, 3),
                "cue_step": contact.cue_step,
                "detecting_drone_id": contact.detecting_drone_id,
                "assigned_drone_id": contact.assigned_drone_id,
                "inspection_attempts": contact.inspection_attempts,
                "resolved": contact.resolved,
                "outcome": contact.outcome,
                "resolution_step": contact.resolution_step,
                "note": contact.note,
            }
            for contact in contacts[:12]
        ]

    def _apply_operator_guidance(self, proposed_goals: dict[int, Position]) -> dict[int, Position]:
        adjusted = dict(proposed_goals)
        for drone in self.drones:
            if drone.id in self.manual_targets:
                adjusted[drone.id] = self.manual_targets[drone.id]
            if drone.id in self.forced_return_overrides:
                adjusted[drone.id] = drone.base_position
            if self._is_excluded(adjusted.get(drone.id, drone.position)):
                adjusted[drone.id] = drone.base_position if drone.id in self.forced_return_overrides else drone.position
        return adjusted

    def _priority_cells(self, limit: int) -> list[Position]:
        assert self.environment is not None
        if not self.priority_zones:
            return []
        weighted_cells: list[tuple[float, Position]] = []
        for position in self.environment.iter_traversable_cells():
            if not self._is_priority(position) or self._is_excluded(position):
                continue
            score = self.probability_map.value_at(position)
            weighted_cells.append((score, position))
        weighted_cells.sort(reverse=True, key=lambda item: item[0])
        return [position for _, position in weighted_cells[:limit]]

    def _is_priority(self, position: Position) -> bool:
        return any(self._position_in_zone(position, zone) for zone in self.priority_zones)

    def _is_excluded(self, position: Position) -> bool:
        return any(self._position_in_zone(position, zone) for zone in self.exclusion_zones)

    @staticmethod
    def _position_in_zone(position: Position, zone: dict[str, Any]) -> bool:
        center = tuple(zone["center"])
        radius = float(zone.get("radius", 1))
        return float(np.hypot(position[0] - center[0], position[1] - center[1])) <= radius

    def _normalize_zone(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "center": self._resolve_open_cell(self._normalize_position(payload["center"])),
            "radius": float(payload.get("radius", 2)),
            "label": str(payload.get("label", "")),
        }

    @staticmethod
    def _normalize_position(position: Any) -> Position:
        x, y = position
        return (int(x), int(y))

    def _get_drone(self, drone_id: int) -> Drone:
        return next(drone for drone in self.drones if drone.id == drone_id)

    def _refresh_communication_links(self) -> None:
        self.communication_links = []
        for drone in self.drones:
            if drone.lifecycle_state in {LIFECYCLE_RECHARGING, LIFECYCLE_READY, LIFECYCLE_UNAVAILABLE}:
                drone.comms_online = True
                drone.last_successful_sync_step = self.current_step
                continue
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
                if drone.lifecycle_state in {LIFECYCLE_RECHARGING, LIFECYCLE_READY, LIFECYCLE_UNAVAILABLE}:
                    continue
                if self._distance(drone.position, drone.base_position) > self.config.communication_radius:
                    self.comms_failures += 1
                    self.logger.record("comms_failure", self.current_step, drone_id=drone.id, mode="out_of_range")
                    continue
                if self.rng.random() < self.config.packet_loss_probability:
                    self.comms_failures += 1
                    self.logger.record("comms_failure", self.current_step, drone_id=drone.id, mode="packet_loss")
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
                if drone_a.lifecycle_state in {LIFECYCLE_RECHARGING, LIFECYCLE_READY, LIFECYCLE_UNAVAILABLE}:
                    continue
                for drone_b in self.drones[index + 1 :]:
                    if drone_b.lifecycle_state in {LIFECYCLE_RECHARGING, LIFECYCLE_READY, LIFECYCLE_UNAVAILABLE}:
                        continue
                    if self._distance(drone_a.position, drone_b.position) > self.config.communication_radius:
                        self.comms_failures += 2
                        self.logger.record("comms_failure", self.current_step, drone_a=drone_a.id, drone_b=drone_b.id, mode="out_of_range")
                        continue
                    for sender, recipient in ((drone_a, drone_b), (drone_b, drone_a)):
                        if self.rng.random() < self.config.packet_loss_probability:
                            self.comms_failures += 1
                            self.logger.record("comms_failure", self.current_step, drone_id=sender.id, recipient_id=recipient.id, mode="packet_loss")
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
        active_search_drones = sum(1 for drone in self.drones if drone.contributes_to_search)
        self.active_search_history.append(float(active_search_drones))
        self.battery_margin_history.extend(drone.battery_margin for drone in self.drones)
        self.metrics.battery_used = float(sum(drone.battery_used for drone in self.drones))
        self.metrics.successful_returns_to_base = self.successful_return_events
        self.metrics.forced_low_battery_returns = self.forced_return_events
        self.metrics.approaching_reserve_events = self.approaching_reserve_events
        self.metrics.critical_battery_events = self.critical_battery_events
        self.metrics.recharge_cycles_started = self.recharge_start_events
        self.metrics.recharge_cycles_completed = self.recharge_complete_events
        self.metrics.redeployments = self.redeploy_events
        self.metrics.rejoined_search_events = self.rejoin_events
        self.metrics.coverage_gap_events = self.coverage_gap_events
        self.metrics.coverage_gap_steps = self.coverage_gap_steps
        self.metrics.average_active_search_drones = (
            float(np.mean(self.active_search_history)) if self.active_search_history else float(active_search_drones)
        )
        self.metrics.battery_margin_min = (
            float(min(self.battery_margin_history)) if self.battery_margin_history else 0.0
        )
        self.metrics.battery_margin_average = (
            float(np.mean(self.battery_margin_history)) if self.battery_margin_history else 0.0
        )
        self.metrics.comms_failures = self.comms_failures
        self.metrics.stale_information_events = self.stale_information_events
        self.metrics.path_efficiency = self.total_direct_cost / self.total_path_cost if self.total_path_cost > 0 else 1.0
        self.metrics.average_overlap_per_step = float(np.mean(self.step_overlap_history)) if self.step_overlap_history else 0.0
        self.metrics.detection_under_comms_mode = self.config.coordination_mode
        current_entropy = self.probability_map.total_entropy()
        self.metrics.entropy_reduction_over_time = max(0.0, self.initial_entropy - current_entropy)
        self.metrics.information_gain_per_step = (
            float(np.mean(self.information_gain_history)) if self.information_gain_history else 0.0
        )
        self.metrics.belief_peak_accuracy = self.probability_map.value_at(self.target.position)
        self.metrics.time_to_first_candidate_detection = self.first_candidate_step
        self.metrics.time_to_confirmed_detection = self.confirmed_detection_step
        self.metrics.candidate_detection_count = self.candidate_detection_events
        self.metrics.inspections_initiated = self.inspection_initiated_events
        self.metrics.inspections_completed = self.inspection_completed_events
        self.metrics.confirmed_contact_count = self.confirmed_contact_events
        self.metrics.rejected_contact_count = self.rejected_contact_events
        self.metrics.false_alarm_count = self.false_alarm_count
        self.metrics.reroute_count = self.reroute_count
        self.metrics.coordination_efficiency = max(
            0.0,
            self.metrics.area_covered_pct / 100.0
            - self.metrics.overlap_ratio * 0.5
            - min(self.metrics.comms_failures / max(self.current_step + 1, 1), 1.0) * 0.1,
        )
        self.metrics.return_to_base_efficiency = (
            self.successful_return_events / self.forced_return_events
            if self.forced_return_events > 0
            else 1.0
        )

    def _record_history(self) -> None:
        self.history.append(self.get_state_snapshot())

    def save_run_artifacts(self, output_dir: str | Path) -> dict[str, Path]:
        """Persist event logs and replay history for a completed run."""

        output_path = Path(output_dir)
        events_path = self.logger.save_jsonl(output_path / "run_events.jsonl")
        replay_path = self.logger.save_replay(self.history, output_path / "run_replay.json")
        return {"events": events_path, "replay": replay_path}
