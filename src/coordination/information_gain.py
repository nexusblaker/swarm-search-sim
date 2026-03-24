"""Information-gain coordination strategy."""

from __future__ import annotations

import numpy as np

from src.agents.drone import Drone
from src.coordination.base import BaseStrategy
from src.environment.grid import GridEnvironment
from src.probability.heatmap import ProbabilityMap


Position = tuple[int, int]


class InformationGainStrategy(BaseStrategy):
    """Choose goals that maximize expected uncertainty reduction."""

    name = "information_gain"

    def select_moves(
        self,
        drones: list[Drone],
        environment: GridEnvironment,
        probability_map: ProbabilityMap,
        step_index: int,
    ) -> dict[int, Position]:
        reserved_cells: set[Position] = set()
        assignments: dict[int, Position] = {}

        for drone in drones:
            if not drone.is_operational:
                assignments[drone.id] = drone.position
                continue

            candidate_cells = self.top_candidate_cells_for_drone(
                drone,
                environment,
                probability_map,
                limit=18,
            )
            best_cell = drone.position
            best_score = float("-inf")
            for candidate in candidate_cells:
                route_cost = self.route_cost(environment, drone.position, candidate)
                belief = self.belief_value(drone, probability_map, candidate)
                local_entropy = self._local_entropy(probability_map.values, candidate)
                footprint = self._candidate_footprint(environment, candidate)
                expected_gain = self._expected_information_gain(
                    probability_map,
                    environment,
                    footprint,
                    fallback=local_entropy,
                )
                overlap_penalty = self.overlap_penalty(drone, candidate)
                reservation_penalty = 1.6 if drone.comms_online and candidate in reserved_cells else 0.0
                battery_factor = max(drone.battery / max(drone.initial_battery, 1.0), 0.1)
                score = 10.0 * belief + 15.0 * expected_gain + 6.0 * local_entropy
                score = battery_factor * score - 0.16 * route_cost
                score -= overlap_penalty + reservation_penalty
                if score > best_score:
                    best_score = score
                    best_cell = candidate
            if drone.comms_online:
                reserved_cells.add(best_cell)
            assignments[drone.id] = best_cell

        return assignments

    @staticmethod
    def _local_entropy(values: np.ndarray, position: Position, radius: int = 1) -> float:
        x, y = position
        min_x = max(0, x - radius)
        max_x = min(values.shape[1], x + radius + 1)
        min_y = max(0, y - radius)
        max_y = min(values.shape[0], y + radius + 1)
        window = values[min_y:max_y, min_x:max_x]
        flattened = window.flatten()
        flattened = flattened[flattened > 0.0]
        if flattened.size == 0:
            return 0.0
        return float(-(flattened * np.log(flattened)).sum())

    @staticmethod
    def _candidate_footprint(
        environment: GridEnvironment,
        position: Position,
        radius: int = 2,
    ) -> set[Position]:
        x0, y0 = position
        cells: set[Position] = set()
        for y in range(max(0, y0 - radius), min(environment.height, y0 + radius + 1)):
            for x in range(max(0, x0 - radius), min(environment.width, x0 + radius + 1)):
                candidate = (x, y)
                if environment.is_obstacle(candidate):
                    continue
                if (x - x0) ** 2 + (y - y0) ** 2 <= radius**2:
                    cells.add(candidate)
        return cells

    @staticmethod
    def _expected_information_gain(
        probability_map: ProbabilityMap,
        environment: GridEnvironment,
        footprint: set[Position],
        fallback: float,
    ) -> float:
        if hasattr(probability_map, "expected_information_gain"):
            return float(probability_map.expected_information_gain(environment, footprint))
        return fallback
