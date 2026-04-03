"""Drone agent models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.simulation.sensing import SENSING_SEARCHING, sensing_label


Position = tuple[int, int]


@dataclass(slots=True)
class Drone:
    """Represents one autonomous search drone in the swarm."""

    id: int
    position: Position
    battery: float
    speed: int
    sensor_range: float
    fov: float
    base_position: Position = (0, 0)
    visited_cells: set[Position] = field(default_factory=set)
    searched_cells: set[Position] = field(default_factory=set)
    path_history: list[Position] = field(default_factory=list)
    planned_path: list[Position] = field(default_factory=list)
    detections: list[dict[str, Any]] = field(default_factory=list)
    intended_target: Position | None = None
    reserved_goal: Position | None = None
    comms_online: bool = True
    local_known_visited: set[Position] = field(default_factory=set)
    local_known_searched: set[Position] = field(default_factory=set)
    known_teammate_targets: dict[int, Position] = field(default_factory=dict)
    local_probability_map: np.ndarray | None = None
    lifecycle_state: str = "deploying"
    operator_status: str = "Deploying"
    sensing_state: str = SENSING_SEARCHING
    sensing_status: str = field(default_factory=lambda: sensing_label(SENSING_SEARCHING))
    assigned_contact_id: str | None = None
    active_contact_position: Position | None = None
    reserve_status: str = "safe"
    reserve_status_label: str = "Safe"
    reserve_reason: str = ""
    returning_to_base: bool = False
    forced_return_triggered: bool = False
    return_completed: bool = False
    energy_required_to_base: float = 0.0
    reserve_required: float = 0.0
    continue_margin_required: float = 0.0
    battery_margin: float = 0.0
    return_eta_steps: int | None = None
    return_service_eta_steps: int | None = None
    turnaround_remaining_steps: int = 0
    sortie_active: bool = False
    ready_since_step: int | None = None
    redeploy_target: Position | None = None
    last_lifecycle_change_step: int = 0
    rejoined_search_step: int | None = None
    sorties_completed: int = 0
    recharge_cycles: int = 0
    redeployments: int = 0
    investigations_started: int = 0
    contacts_confirmed: int = 0
    contacts_rejected: int = 0
    stale_steps: int = 0
    last_successful_sync_step: int = 0
    heading: tuple[int, int] = (0, 1)
    initial_battery: float = field(init=False)

    def __post_init__(self) -> None:
        self.initial_battery = self.battery
        self.battery_margin = self.battery
        self.visited_cells.add(self.position)
        self.local_known_visited.add(self.position)
        self.path_history.append(self.position)

    def move_to(self, position: Position, movement_cost: float) -> None:
        """Move the drone and reduce its remaining battery budget."""

        previous_position = self.position
        self.position = position
        self.visited_cells.add(position)
        self.local_known_visited.add(position)
        self.path_history.append(position)
        self.heading = (
            position[0] - previous_position[0],
            position[1] - previous_position[1],
        )
        self.battery = max(0.0, self.battery - movement_cost)

    def record_detection(
        self,
        step: int,
        target_position: Position,
        confidence: float,
        is_true_positive: bool,
        stage: str = "cue",
        outcome: str | None = None,
        contact_id: str | None = None,
    ) -> None:
        """Store a sensor detection event for later analysis."""

        self.detections.append(
            {
                "step": step,
                "target_position": target_position,
                "confidence": confidence,
                "is_true_positive": is_true_positive,
                "stage": stage,
                "outcome": outcome,
                "contact_id": contact_id,
            }
        )

    @property
    def battery_used(self) -> float:
        """Return battery consumed since the start of the mission."""

        return self.initial_battery - self.battery

    @property
    def is_operational(self) -> bool:
        """Return whether the drone can continue moving and scanning."""

        return self.battery > 0.0

    @property
    def can_scan(self) -> bool:
        """Return whether the drone should contribute sensing at this moment."""

        return self.is_operational and self.lifecycle_state not in {
            "returning_to_base",
            "recharging_or_swapping",
            "ready_to_redeploy",
            "unavailable",
        }

    @property
    def contributes_to_search(self) -> bool:
        """Return whether the drone is actively contributing to coverage."""

        return self.can_scan and self.lifecycle_state in {"searching", "redeploying", "deploying"} and self.sensing_state == SENSING_SEARCHING

    @property
    def distance_from_base(self) -> int:
        """Return Manhattan distance from the launch base."""

        return abs(self.position[0] - self.base_position[0]) + abs(
            self.position[1] - self.base_position[1]
        )
