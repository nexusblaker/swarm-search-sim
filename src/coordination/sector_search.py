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
        self._sector_bounds: dict[int, tuple[int, int]] = {}

    def reset(self, environment: GridEnvironment, drones: list[Drone]) -> None:
        self._sector_paths = {}
        self._sector_bounds = {}
        sector_width = max(1, environment.width // max(len(drones), 1))
        for index, drone in enumerate(drones):
            start_x = index * sector_width
            end_x = environment.width if index == len(drones) - 1 else min(environment.width, start_x + sector_width)
            self._sector_bounds[drone.id] = (start_x, end_x)
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
            if not drone.is_operational:
                moves[drone.id] = drone.position
                continue

            planned_path = self._sector_paths.get(drone.id, [])
            sector_cells = [
                cell
                for cell in planned_path
                if cell not in drone.visited_cells
            ]
            target = sector_cells[0] if sector_cells else self._best_local_probability_cell(
                drone=drone,
                environment=environment,
                probability_map=probability_map,
            )
            moves[drone.id] = self._step_towards(drone.position, target, environment)
        return moves

    def _best_local_probability_cell(
        self,
        drone: Drone,
        environment: GridEnvironment,
        probability_map: ProbabilityMap,
    ) -> Position:
        start_x, end_x = self._sector_bounds.get(drone.id, (0, environment.width))
        best_cell = drone.position
        best_score = float("-inf")
        for y in range(environment.height):
            for x in range(start_x, end_x):
                candidate = (x, y)
                if environment.is_obstacle(candidate):
                    continue
                score = probability_map.value_at(candidate) - 0.01 * (
                    abs(x - drone.position[0]) + abs(y - drone.position[1])
                )
                if score > best_score:
                    best_score = score
                    best_cell = candidate
        return best_cell

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
