"""Drone agent models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


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
    returning_to_base: bool = False
    forced_return_triggered: bool = False
    return_completed: bool = False
    stale_steps: int = 0
    last_successful_sync_step: int = 0
    heading: tuple[int, int] = (0, 1)
    initial_battery: float = field(init=False)

    def __post_init__(self) -> None:
        self.initial_battery = self.battery
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
    ) -> None:
        """Store a sensor detection event for later analysis."""

        self.detections.append(
            {
                "step": step,
                "target_position": target_position,
                "confidence": confidence,
                "is_true_positive": is_true_positive,
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
    def distance_from_base(self) -> int:
        """Return Manhattan distance from the launch base."""

        return abs(self.position[0] - self.base_position[0]) + abs(
            self.position[1] - self.base_position[1]
        )
