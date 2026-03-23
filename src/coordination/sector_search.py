"""Sector-based coordination strategy."""

from __future__ import annotations

from src.agents.drone import Drone
from src.coordination.base import BaseStrategy
from src.environment.grid import GridEnvironment
from src.probability.heatmap import ProbabilityMap


Position = tuple[int, int]


class SectorSearchStrategy(BaseStrategy):
    """Assign each drone a vertical sector and sweep it in a lawnmower pattern."""

    name = "sector_search"

    def __init__(self, rng=None) -> None:
        super().__init__(rng=rng)
        self._sector_paths: dict[int, list[Position]] = {}

    def reset(self, environment: GridEnvironment, drones: list[Drone]) -> None:
        self._sector_paths = {}
        sector_width = max(1, environment.width // max(len(drones), 1))
        for index, drone in enumerate(drones):
            start_x = index * sector_width
            end_x = environment.width if index == len(drones) - 1 else min(environment.width, start_x + sector_width)
            path: list[Position] = []
            for y in range(environment.height):
                x_values = range(start_x, end_x)
                if y % 2 == 1:
                    x_values = reversed(list(x_values))
                for x in x_values:
                    position = (x, y)
                    if not environment.is_obstacle(position):
                        path.append(position)
            self._sector_paths[drone.id] = path

    def select_moves(
        self,
        drones: list[Drone],
        environment: GridEnvironment,
        probability_map: ProbabilityMap,
        step_index: int,
    ) -> dict[int, Position]:
        moves: dict[int, Position] = {}
        for drone in drones:
            planned_path = self._sector_paths.get(drone.id, [])
            target = next(
                (cell for cell in planned_path if cell not in drone.visited_cells),
                drone.position,
            )
            moves[drone.id] = self._step_towards(drone.position, target, environment)
        return moves

    @staticmethod
    def _step_towards(current: Position, target: Position, environment: GridEnvironment) -> Position:
        if current == target:
            return current

        cx, cy = current
        tx, ty = target
        step = (
            cx + (1 if tx > cx else -1 if tx < cx else 0),
            cy + (1 if ty > cy else -1 if ty < cy else 0),
        )
        if environment.in_bounds(step) and not environment.is_obstacle(step):
            return step

        fallback_moves = environment.get_neighbors(current, diagonal=True)
        if not fallback_moves:
            return current
        return min(
            fallback_moves,
            key=lambda candidate: abs(candidate[0] - tx) + abs(candidate[1] - ty),
        )
