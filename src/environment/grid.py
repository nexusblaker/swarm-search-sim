"""Terrain-aware grid environment for swarm search simulation."""

from __future__ import annotations

from enum import IntEnum
from typing import Iterable

import numpy as np


Position = tuple[int, int]


class TerrainType(IntEnum):
    """Supported terrain classes for the simulation grid."""

    PLAIN = 0
    FOREST = 1
    HILL = 2
    URBAN = 3
    WATER = 4


class GridEnvironment:
    """Represents the search environment and terrain-derived traversal metadata."""

    TERRAIN_PROPERTIES: dict[TerrainType, tuple[float, float]] = {
        TerrainType.PLAIN: (1.0, 1.0),
        TerrainType.FOREST: (1.4, 0.7),
        TerrainType.HILL: (1.8, 0.8),
        TerrainType.URBAN: (1.2, 0.9),
        TerrainType.WATER: (2.5, 0.45),
    }

    def __init__(
        self,
        terrain_grid: np.ndarray,
        movement_cost: np.ndarray,
        detection_modifier: np.ndarray,
        obstacle_mask: np.ndarray,
    ) -> None:
        self.terrain_grid = terrain_grid.astype(int)
        self.movement_cost = movement_cost.astype(float)
        self.detection_modifier = detection_modifier.astype(float)
        self.obstacle_mask = obstacle_mask.astype(bool)
        self.height, self.width = self.terrain_grid.shape

    @classmethod
    def generate(
        cls,
        width: int,
        height: int,
        rng: np.random.Generator,
        obstacle_ratio: float = 0.05,
        terrain_distribution: dict[str, float] | None = None,
    ) -> "GridEnvironment":
        """Generate a procedural environment from a seeded random generator."""

        terrain_distribution = terrain_distribution or {
            "plain": 0.45,
            "forest": 0.2,
            "hill": 0.15,
            "urban": 0.15,
            "water": 0.05,
        }
        terrain_keys = [
            TerrainType.PLAIN,
            TerrainType.FOREST,
            TerrainType.HILL,
            TerrainType.URBAN,
            TerrainType.WATER,
        ]
        weights = np.array(
            [
                terrain_distribution.get("plain", 0.45),
                terrain_distribution.get("forest", 0.2),
                terrain_distribution.get("hill", 0.15),
                terrain_distribution.get("urban", 0.15),
                terrain_distribution.get("water", 0.05),
            ],
            dtype=float,
        )
        weights = weights / weights.sum()

        terrain_indices = rng.choice(len(terrain_keys), size=(height, width), p=weights)
        terrain_grid = np.vectorize(lambda idx: int(terrain_keys[idx]))(terrain_indices)

        movement_cost = np.zeros((height, width), dtype=float)
        detection_modifier = np.zeros((height, width), dtype=float)
        for terrain in terrain_keys:
            terrain_mask = terrain_grid == int(terrain)
            move_cost, detect_mod = cls.TERRAIN_PROPERTIES[terrain]
            movement_cost[terrain_mask] = move_cost
            detection_modifier[terrain_mask] = detect_mod

        obstacle_mask = rng.random((height, width)) < obstacle_ratio
        obstacle_mask &= terrain_grid != int(TerrainType.WATER)

        return cls(
            terrain_grid=terrain_grid,
            movement_cost=movement_cost,
            detection_modifier=detection_modifier,
            obstacle_mask=obstacle_mask,
        )

    @property
    def shape(self) -> tuple[int, int]:
        """Return the environment shape as (height, width)."""

        return self.terrain_grid.shape

    @property
    def traversable_cell_count(self) -> int:
        """Return the number of cells that drones can traverse."""

        return int(np.size(self.obstacle_mask) - np.count_nonzero(self.obstacle_mask))

    def in_bounds(self, position: Position) -> bool:
        """Check whether a coordinate is inside the grid."""

        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def is_obstacle(self, position: Position) -> bool:
        """Return whether a cell is blocked for traversal."""

        if not self.in_bounds(position):
            return True
        x, y = position
        return bool(self.obstacle_mask[y, x])

    def terrain_at(self, position: Position) -> TerrainType:
        """Return terrain type at a coordinate."""

        x, y = position
        return TerrainType(int(self.terrain_grid[y, x]))

    def get_movement_cost(self, position: Position) -> float:
        """Return the movement cost for a cell."""

        x, y = position
        return float(self.movement_cost[y, x])

    def get_detection_modifier(self, position: Position) -> float:
        """Return the thermal detection modifier for a cell."""

        x, y = position
        return float(self.detection_modifier[y, x])

    def get_neighbors(self, position: Position, diagonal: bool = False) -> list[Position]:
        """Return valid neighboring cells."""

        x, y = position
        offsets: Iterable[tuple[int, int]] = ((1, 0), (-1, 0), (0, 1), (0, -1))
        if diagonal:
            offsets = (
                (1, 0),
                (-1, 0),
                (0, 1),
                (0, -1),
                (1, 1),
                (1, -1),
                (-1, 1),
                (-1, -1),
            )

        neighbors: list[Position] = []
        for dx, dy in offsets:
            candidate = (x + dx, y + dy)
            if self.in_bounds(candidate) and not self.is_obstacle(candidate):
                neighbors.append(candidate)
        return neighbors

    def iter_traversable_cells(self) -> Iterable[Position]:
        """Yield traversable cells in row-major order."""

        for y in range(self.height):
            for x in range(self.width):
                position = (x, y)
                if not self.is_obstacle(position):
                    yield position
