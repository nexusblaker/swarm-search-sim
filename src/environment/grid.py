"""Terrain-aware grid environment for swarm search simulation."""

from __future__ import annotations

from enum import IntEnum
from pathlib import Path
from typing import Iterable

import json

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
        trail_layer: np.ndarray | None = None,
        elevation_layer: np.ndarray | None = None,
        wind_layer: np.ndarray | None = None,
    ) -> None:
        self.terrain_grid = terrain_grid.astype(int)
        self.movement_cost = movement_cost.astype(float)
        self.detection_modifier = detection_modifier.astype(float)
        self.obstacle_mask = obstacle_mask.astype(bool)
        self.trail_layer = (
            trail_layer.astype(bool)
            if trail_layer is not None
            else np.zeros_like(self.obstacle_mask, dtype=bool)
        )
        self.elevation_layer = (
            elevation_layer.astype(float)
            if elevation_layer is not None
            else np.zeros_like(self.movement_cost, dtype=float)
        )
        self.wind_layer = (
            wind_layer.astype(float)
            if wind_layer is not None
            else np.zeros_like(self.movement_cost, dtype=float)
        )
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

        trail_layer = np.zeros((height, width), dtype=bool)
        elevation_layer = np.zeros((height, width), dtype=float)
        wind_layer = np.zeros((height, width), dtype=float)
        return cls(
            terrain_grid=terrain_grid,
            movement_cost=movement_cost,
            detection_modifier=detection_modifier,
            obstacle_mask=obstacle_mask,
            trail_layer=trail_layer,
            elevation_layer=elevation_layer,
            wind_layer=wind_layer,
        )

    @classmethod
    def from_layers(
        cls,
        terrain_grid: np.ndarray,
        obstacle_mask: np.ndarray,
        trail_layer: np.ndarray | None = None,
        elevation_layer: np.ndarray | None = None,
        wind_layer: np.ndarray | None = None,
    ) -> "GridEnvironment":
        """Build an environment from externally defined layers."""

        terrain_grid = terrain_grid.astype(int)
        height, width = terrain_grid.shape
        trail_layer = trail_layer if trail_layer is not None else np.zeros((height, width), dtype=bool)
        elevation_layer = elevation_layer if elevation_layer is not None else np.zeros((height, width), dtype=float)
        wind_layer = wind_layer if wind_layer is not None else np.zeros((height, width), dtype=float)

        movement_cost = np.zeros((height, width), dtype=float)
        detection_modifier = np.zeros((height, width), dtype=float)
        for terrain in TerrainType:
            terrain_mask = terrain_grid == int(terrain)
            move_cost, detect_mod = cls.TERRAIN_PROPERTIES[terrain]
            movement_cost[terrain_mask] = move_cost
            detection_modifier[terrain_mask] = detect_mod

        slope_penalty = cls._compute_slope_penalty(elevation_layer)
        movement_cost += slope_penalty
        movement_cost[trail_layer.astype(bool)] = np.maximum(0.65, movement_cost[trail_layer.astype(bool)] - 0.35)
        detection_modifier[trail_layer.astype(bool)] = np.minimum(
            1.05,
            detection_modifier[trail_layer.astype(bool)] + 0.08,
        )

        return cls(
            terrain_grid=terrain_grid,
            movement_cost=movement_cost,
            detection_modifier=detection_modifier,
            obstacle_mask=obstacle_mask,
            trail_layer=trail_layer,
            elevation_layer=elevation_layer,
            wind_layer=wind_layer,
        )

    @classmethod
    def load_layers(cls, layer_paths: dict[str, str | Path]) -> "GridEnvironment":
        """Load terrain and optional environment layers from disk."""

        terrain_grid = cls._load_array(layer_paths["terrain"], dtype=int)
        obstacle_mask = cls._load_array(layer_paths["obstacle"], dtype=int).astype(bool)
        trail_layer = (
            cls._load_array(layer_paths["trail"], dtype=int).astype(bool)
            if "trail" in layer_paths
            else None
        )
        elevation_layer = (
            cls._load_array(layer_paths["elevation"], dtype=float)
            if "elevation" in layer_paths
            else None
        )
        wind_layer = (
            cls._load_array(layer_paths["wind"], dtype=float)
            if "wind" in layer_paths
            else None
        )
        return cls.from_layers(
            terrain_grid=terrain_grid,
            obstacle_mask=obstacle_mask,
            trail_layer=trail_layer,
            elevation_layer=elevation_layer,
            wind_layer=wind_layer,
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

    def get_wind_factor(self, position: Position) -> float:
        """Return local wind intensity for a cell."""

        x, y = position
        return float(self.wind_layer[y, x])

    def has_trail(self, position: Position) -> bool:
        """Return whether a traversable trail or road is present at a cell."""

        x, y = position
        return bool(self.trail_layer[y, x])

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

    def estimate_cost(self, start: Position, goal: Position) -> float:
        """Return a lightweight admissible-ish cost estimate for path planning."""

        dx = abs(start[0] - goal[0])
        dy = abs(start[1] - goal[1])
        return float((dx + dy) * np.min(self.movement_cost))

    def line_cells(self, start: Position, end: Position) -> list[Position]:
        """Return grid cells along a line segment between two points."""

        x0, y0 = start
        x1, y1 = end
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        cells: list[Position] = []
        for step in range(steps + 1):
            t = step / steps
            x = int(round(x0 + (x1 - x0) * t))
            y = int(round(y0 + (y1 - y0) * t))
            position = (x, y)
            if not cells or cells[-1] != position:
                cells.append(position)
        return cells

    def has_line_of_sight(self, start: Position, end: Position) -> bool:
        """Approximate line of sight using obstacles and high-blockage terrain."""

        obstruction_score = 0.0
        for cell in self.line_cells(start, end)[1:-1]:
            if self.is_obstacle(cell):
                return False
            terrain = self.terrain_at(cell)
            if terrain == TerrainType.FOREST:
                obstruction_score += 0.35
            elif terrain == TerrainType.HILL:
                obstruction_score += 0.2
            elif terrain == TerrainType.URBAN:
                obstruction_score += 0.25
            elif terrain == TerrainType.WATER:
                obstruction_score += 0.1
        return obstruction_score < 1.2

    def iter_traversable_cells(self) -> Iterable[Position]:
        """Yield traversable cells in row-major order."""

        for y in range(self.height):
            for x in range(self.width):
                position = (x, y)
                if not self.is_obstacle(position):
                    yield position

    @staticmethod
    def _compute_slope_penalty(elevation_layer: np.ndarray) -> np.ndarray:
        grad_y, grad_x = np.gradient(elevation_layer.astype(float))
        return 0.35 * np.hypot(grad_x, grad_y)

    @staticmethod
    def _load_array(path: str | Path, dtype: type[int] | type[float]) -> np.ndarray:
        file_path = Path(path)
        if file_path.suffix == ".npy":
            return np.load(file_path).astype(dtype)
        if file_path.suffix == ".json":
            return np.asarray(json.loads(file_path.read_text(encoding="utf-8")), dtype=dtype)
        return np.loadtxt(file_path, delimiter=",", dtype=dtype)
