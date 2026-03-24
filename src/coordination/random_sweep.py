"""Randomized sweep coordination strategy."""

from __future__ import annotations

from src.agents.drone import Drone
from src.coordination.base import BaseStrategy
from src.environment.grid import GridEnvironment
from src.probability.heatmap import ProbabilityMap


class RandomSweepStrategy(BaseStrategy):
    """Simple exploration strategy favoring unvisited neighboring cells."""

    name = "random_sweep"

    def __init__(self, rng=None) -> None:
        super().__init__(rng=rng)
        self._last_move: dict[int, tuple[int, int]] = {}

    def select_moves(
        self,
        drones: list[Drone],
        environment: GridEnvironment,
        probability_map: ProbabilityMap,
        step_index: int,
    ) -> dict[int, tuple[int, int]]:
        moves: dict[int, tuple[int, int]] = {}
        for drone in drones:
            if not drone.is_operational:
                moves[drone.id] = drone.position
                continue

            candidates = self.candidate_moves(drone, environment)
            best_score = float("-inf")
            best_candidate = drone.position
            previous_position = (
                drone.path_history[-2]
                if len(drone.path_history) > 1
                else drone.position
            )
            for candidate in candidates:
                unvisited_bonus = 1.8 if candidate not in drone.visited_cells else -0.5
                probability_bonus = probability_map.value_at(candidate) * 2.5
                movement_penalty = environment.get_movement_cost(candidate) * 0.2
                backtrack_penalty = 0.6 if candidate == previous_position else 0.0
                noise = float(self.rng.uniform(0.0, 1.0))
                score = unvisited_bonus + probability_bonus + noise - movement_penalty - backtrack_penalty
                if score > best_score:
                    best_score = score
                    best_candidate = candidate
            self._last_move[drone.id] = best_candidate
            moves[drone.id] = best_candidate
        return moves
