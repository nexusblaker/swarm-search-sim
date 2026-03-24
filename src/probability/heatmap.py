"""Probability map utilities for uncertain target localization."""

from __future__ import annotations

from typing import Iterable

import numpy as np

from src.environment.grid import GridEnvironment


Position = tuple[int, int]


class ProbabilityMap:
    """Represents a terrain-weighted target belief distribution over the grid."""

    def __init__(
        self,
        grid_shape: tuple[int, int],
        last_known_position: Position,
        sigma: float = 5.0,
    ) -> None:
        self.grid_shape = grid_shape
        self.last_known_position = last_known_position
        self.sigma = sigma
        self.values = self._build_gaussian(grid_shape, last_known_position, sigma)
        self.normalize()

    @staticmethod
    def _build_gaussian(
        grid_shape: tuple[int, int],
        center: Position,
        sigma: float,
    ) -> np.ndarray:
        height, width = grid_shape
        center_x, center_y = center
        y_indices, x_indices = np.indices((height, width))
        squared_distance = (x_indices - center_x) ** 2 + (y_indices - center_y) ** 2
        sigma = max(sigma, 1e-3)
        return np.exp(-squared_distance / (2.0 * sigma**2))

    def normalize(self) -> None:
        """Normalize the probability grid to sum to one."""

        total_mass = float(self.values.sum())
        if total_mass <= 0.0:
            self.values.fill(1.0 / self.values.size)
            return
        self.values /= total_mass

    def apply_terrain_weighting(self, environment: GridEnvironment) -> None:
        """Bias the belief map toward more traversable and detectable terrain."""

        traversability_weight = 1.0 / np.maximum(environment.movement_cost, 1e-3)
        terrain_weight = traversability_weight * environment.detection_modifier
        terrain_weight[environment.obstacle_mask] = 0.0
        self.values *= terrain_weight
        self.normalize()

    def diffuse(self, environment: GridEnvironment, diffusion_rate: float = 0.08) -> None:
        """Diffuse probability mass over traversable neighboring cells."""

        self.values = self.diffuse_values(self.values, environment, diffusion_rate)
        self.normalize()

    def update_after_negative_search(
        self,
        searched_cells: Iterable[Position],
        suppression: float = 0.25,
        search_counts: dict[Position, int] | None = None,
    ) -> None:
        """Reduce belief in searched cells after no target is found."""

        self.values = self.suppress_values(
            self.values,
            searched_cells,
            suppression,
            search_counts,
        )
        self.normalize()

    def value_at(self, position: Position) -> float:
        """Return the probability mass at a specific cell."""

        x, y = position
        return float(self.values[y, x])

    def mass_in_cells(self, cells: Iterable[Position]) -> float:
        """Return total probability mass contained in a collection of cells."""

        return float(sum(self.value_at(cell) for cell in cells))

    def highest_probability_cell(self) -> Position:
        """Return the current argmax cell of the belief map."""

        index = int(np.argmax(self.values))
        y, x = np.unravel_index(index, self.values.shape)
        return (int(x), int(y))

    @staticmethod
    def diffuse_values(
        values: np.ndarray,
        environment: GridEnvironment,
        diffusion_rate: float,
    ) -> np.ndarray:
        """Return a diffused copy of a probability grid."""

        if diffusion_rate <= 0.0:
            return values.copy()

        next_values = np.zeros_like(values)
        for position in environment.iter_traversable_cells():
            x, y = position
            neighbors = environment.get_neighbors(position, diagonal=True)
            retained_mass = values[y, x] * (1.0 - diffusion_rate)
            next_values[y, x] += retained_mass

            transferred_mass = values[y, x] * diffusion_rate
            if not neighbors:
                next_values[y, x] += transferred_mass
                continue

            weights = np.array(
                [
                    (1.0 / environment.get_movement_cost(neighbor))
                    * (1.2 - environment.get_detection_modifier(neighbor))
                    for neighbor in neighbors
                ],
                dtype=float,
            )
            weights = np.clip(weights, 1e-3, None)
            weights /= weights.sum()
            for neighbor, weight in zip(neighbors, weights):
                nx, ny = neighbor
                next_values[ny, nx] += transferred_mass * weight

        next_values[environment.obstacle_mask] = 0.0
        total = float(next_values.sum())
        if total > 0.0:
            next_values /= total
        return next_values

    @staticmethod
    def suppress_values(
        values: np.ndarray,
        searched_cells: Iterable[Position],
        suppression: float,
        search_counts: dict[Position, int] | None = None,
    ) -> np.ndarray:
        """Return a copy of a probability grid after negative evidence updates."""

        next_values = values.copy()
        for x, y in searched_cells:
            if 0 <= y < next_values.shape[0] and 0 <= x < next_values.shape[1]:
                repeat_factor = 1.0
                if search_counts is not None:
                    repeat_factor += 0.25 * max(search_counts.get((x, y), 0) - 1, 0)
                effective_suppression = max(0.02, suppression / repeat_factor)
                next_values[y, x] *= effective_suppression
        next_values = np.clip(next_values, 0.0, None)
        total = float(next_values.sum())
        if total > 0.0:
            next_values /= total
        return next_values
