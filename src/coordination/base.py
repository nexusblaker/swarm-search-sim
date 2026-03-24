"""Coordination strategy interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from src.agents.drone import Drone
from src.environment.grid import GridEnvironment
from src.probability.heatmap import ProbabilityMap
from src.simulation.planning import astar_path, path_cost


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
        """Return the desired goal position for each drone."""

    @staticmethod
    def candidate_moves(drone: Drone, environment: GridEnvironment) -> list[Position]:
        """Return legal move candidates for a drone, including staying in place."""

        moves = environment.get_neighbors(drone.position, diagonal=True)
        if drone.position not in moves:
            moves.append(drone.position)
        return moves

    @staticmethod
    def belief_value(
        drone: Drone,
        probability_map: ProbabilityMap,
        candidate: Position,
    ) -> float:
        """Return a belief value using local knowledge when available."""

        if drone.local_probability_map is not None:
            x, y = candidate
            return float(drone.local_probability_map[y, x])
        return probability_map.value_at(candidate)

    @staticmethod
    def overlap_penalty(drone: Drone, candidate: Position) -> float:
        """Return a penalty for cells believed to be already covered."""

        penalty = 0.0
        if candidate in drone.local_known_searched:
            penalty += 0.9
        if candidate in drone.local_known_visited:
            penalty += 0.35
        if candidate in drone.known_teammate_targets.values():
            penalty += 1.1
        return penalty

    @staticmethod
    def top_candidate_cells(
        environment: GridEnvironment,
        probability_map: ProbabilityMap,
        limit: int = 16,
    ) -> list[Position]:
        """Return high-probability traversable candidate cells."""

        values = probability_map.values
        flat_indices = np.argsort(values, axis=None)[::-1]
        candidates: list[Position] = []
        for index in flat_indices:
            y, x = np.unravel_index(int(index), values.shape)
            candidate = (int(x), int(y))
            if environment.is_obstacle(candidate):
                continue
            candidates.append(candidate)
            if len(candidates) >= limit:
                break
        return candidates

    @staticmethod
    def top_candidate_cells_for_drone(
        drone: Drone,
        environment: GridEnvironment,
        probability_map: ProbabilityMap,
        limit: int = 16,
    ) -> list[Position]:
        """Return high-value candidate cells using a drone's local belief when available."""

        values = drone.local_probability_map if drone.local_probability_map is not None else probability_map.values
        flat_indices = np.argsort(values, axis=None)[::-1]
        candidates: list[Position] = []
        for index in flat_indices:
            y, x = np.unravel_index(int(index), values.shape)
            candidate = (int(x), int(y))
            if environment.is_obstacle(candidate):
                continue
            candidates.append(candidate)
            if len(candidates) >= limit:
                break
        return candidates

    @staticmethod
    def route_cost(
        environment: GridEnvironment,
        start: Position,
        goal: Position,
        blocked: set[Position] | None = None,
    ) -> float:
        """Compute a terrain-aware path cost between two cells."""

        return path_cost(environment, astar_path(environment, start, goal, blocked=blocked))
