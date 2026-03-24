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
        reserved_cells: set[tuple[int, int]] = set()
        global_visited = set().union(*(drone.visited_cells for drone in drones))
        for drone in drones:
            if not drone.is_operational:
                moves[drone.id] = drone.position
                continue

            candidates = self.candidate_moves(drone, environment)
            best_candidate = drone.position
            best_score = float("-inf")
            for candidate in candidates:
                probability_score = probability_map.value_at(candidate) * 18.0
                revisit_penalty = 0.9 if candidate in drone.visited_cells else 0.0
                global_overlap_penalty = 0.35 if candidate in global_visited else 0.0
                reservation_penalty = 2.0 if candidate in reserved_cells else 0.0
                mobility_penalty = environment.get_movement_cost(candidate) * 0.3
                score = (
                    probability_score
                    - revisit_penalty
                    - global_overlap_penalty
                    - reservation_penalty
                    - mobility_penalty
                )
                if score > best_score:
                    best_candidate = candidate
                    best_score = score
            reserved_cells.add(best_candidate)
            moves[drone.id] = best_candidate
        return moves
