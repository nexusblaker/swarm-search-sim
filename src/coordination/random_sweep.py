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

            traversable_cells = list(environment.iter_traversable_cells())
            sampled_candidates = list(
                self.rng.choice(
                    traversable_cells,
                    size=min(12, len(traversable_cells)),
                    replace=False,
                )
            )
            best_score = float("-inf")
            best_candidate = drone.position
            for candidate in sampled_candidates:
                path_cost = self.route_cost(environment, drone.position, tuple(candidate))
                unsearched_bonus = 1.5 if tuple(candidate) not in drone.local_known_searched else -0.3
                probability_bonus = self.belief_value(drone, probability_map, tuple(candidate)) * 4.0
                noise = float(self.rng.uniform(0.0, 1.2))
                score = unsearched_bonus + probability_bonus + noise - 0.12 * path_cost
                if score > best_score:
                    best_score = score
                    best_candidate = tuple(candidate)
            self._last_move[drone.id] = best_candidate
            moves[drone.id] = best_candidate
        return moves
