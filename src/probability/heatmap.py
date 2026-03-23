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

    def update_after_negative_search(
        self,
        searched_cells: Iterable[Position],
        suppression: float = 0.25,
    ) -> None:
        """Reduce belief in searched cells after no target is found."""

        for x, y in searched_cells:
            if 0 <= y < self.values.shape[0] and 0 <= x < self.values.shape[1]:
                self.values[y, x] *= suppression
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
