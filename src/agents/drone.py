"""Drone agent models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    visited_cells: set[Position] = field(default_factory=set)
    detections: list[dict[str, Any]] = field(default_factory=list)
    comms_online: bool = True
    initial_battery: float = field(init=False)

    def __post_init__(self) -> None:
        self.initial_battery = self.battery
        self.visited_cells.add(self.position)

    def move_to(self, position: Position, movement_cost: float) -> None:
        """Move the drone and reduce its remaining battery budget."""

        self.position = position
        self.visited_cells.add(position)
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
