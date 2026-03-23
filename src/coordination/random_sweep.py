"""Randomized sweep coordination strategy."""

from __future__ import annotations

from src.agents.drone import Drone
from src.coordination.base import BaseStrategy
from src.environment.grid import GridEnvironment
from src.probability.heatmap import ProbabilityMap


class RandomSweepStrategy(BaseStrategy):
    """Simple exploration strategy favoring unvisited neighboring cells."""

    name = "random_sweep"

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
            best_score = float("-inf")
            best_candidate = drone.position
            for candidate in candidates:
                unvisited_bonus = 1.0 if candidate not in drone.visited_cells else -0.2
                probability_bonus = probability_map.value_at(candidate) * 5.0
                noise = float(self.rng.uniform(0.0, 0.2))
                score = unvisited_bonus + probability_bonus + noise
                if score > best_score:
                    best_score = score
                    best_candidate = candidate
            moves[drone.id] = best_candidate
        return moves
