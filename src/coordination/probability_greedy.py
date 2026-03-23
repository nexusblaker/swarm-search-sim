"""Probability-greedy coordination strategy."""

from __future__ import annotations

from src.agents.drone import Drone
from src.coordination.base import BaseStrategy
from src.environment.grid import GridEnvironment
from src.probability.heatmap import ProbabilityMap


class ProbabilityGreedyStrategy(BaseStrategy):
    """Greedily moves each drone toward locally high probability cells."""

    name = "probability_greedy"

    def select_moves(
        self,
        drones: list[Drone],
        environment: GridEnvironment,
        probability_map: ProbabilityMap,
        step_index: int,
    ) -> dict[int, tuple[int, int]]:
        moves: dict[int, tuple[int, int]] = {}
        for drone in drones:
            candidates = self.candidate_moves(drone, environment)
            best_candidate = drone.position
            best_score = float("-inf")
            for candidate in candidates:
                probability_score = probability_map.value_at(candidate) * 10.0
                revisit_penalty = 0.75 if candidate in drone.visited_cells else 0.0
                mobility_penalty = environment.get_movement_cost(candidate) * 0.25
                score = probability_score - revisit_penalty - mobility_penalty
                if score > best_score:
                    best_candidate = candidate
                    best_score = score
            moves[drone.id] = best_candidate
        return moves
