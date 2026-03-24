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
        for drone in drones:
            if not drone.is_operational:
                moves[drone.id] = drone.position
                continue

            candidate_goals = self.top_candidate_cells_for_drone(
                drone,
                environment,
                probability_map,
                limit=18,
            )
            best_candidate = drone.position
            best_score = float("-inf")
            for candidate in candidate_goals:
                probability_score = self.belief_value(drone, probability_map, candidate) * 22.0
                route_cost = self.route_cost(environment, drone.position, candidate)
                reservation_penalty = 2.0 if drone.comms_online and candidate in reserved_cells else 0.0
                overlap_penalty = self.overlap_penalty(drone, candidate)
                score = (
                    probability_score
                    - overlap_penalty
                    - reservation_penalty
                    - 0.18 * route_cost
                )
                if score > best_score:
                    best_candidate = candidate
                    best_score = score
            if drone.comms_online:
                reserved_cells.add(best_candidate)
            moves[drone.id] = best_candidate
        return moves
