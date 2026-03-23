"""Coordination strategy interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from src.agents.drone import Drone
from src.environment.grid import GridEnvironment
from src.probability.heatmap import ProbabilityMap


Position = tuple[int, int]


class BaseStrategy(ABC):
    """Abstract coordination policy used by the simulation engine."""

    name = "base"

    def __init__(self, rng: np.random.Generator | None = None) -> None:
        self.rng = rng or np.random.default_rng()

    def reset(self, environment: GridEnvironment, drones: list[Drone]) -> None:
        """Reset any internal state before a mission starts."""

    @abstractmethod
    def select_moves(
        self,
        drones: list[Drone],
        environment: GridEnvironment,
        probability_map: ProbabilityMap,
        step_index: int,
    ) -> dict[int, Position]:
        """Return the desired next position for each drone."""

    @staticmethod
    def candidate_moves(drone: Drone, environment: GridEnvironment) -> list[Position]:
        """Return legal move candidates for a drone, including staying in place."""

        moves = environment.get_neighbors(drone.position, diagonal=True)
        if drone.position not in moves:
            moves.append(drone.position)
        return moves
