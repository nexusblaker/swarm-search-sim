"""Belief-state extensions for target tracking and information planning."""

from __future__ import annotations

from typing import Iterable

import numpy as np

from src.environment.grid import GridEnvironment, TerrainType
from src.probability.heatmap import Position, ProbabilityMap


class BeliefState(ProbabilityMap):
    """Belief-state model with motion propagation and observation updates."""

    def propagate(
        self,
        environment: GridEnvironment,
        target_behavior: str,
        motion_strength: float = 0.18,
    ) -> None:
        self.values = self.propagate_values(
            self.values,
            environment,
            target_behavior=target_behavior,
            motion_strength=motion_strength,
        )
        self.normalize()

    def update_from_observations(
        self,
        scanned_cells: Iterable[Position],
        positive_cells: dict[Position, float] | None = None,
        suppression: float = 0.2,
        positive_gain: float = 1.6,
        search_counts: dict[Position, int] | None = None,
    ) -> None:
        updated = self.suppress_values(
            self.values,
            searched_cells=scanned_cells,
            suppression=suppression,
            search_counts=search_counts,
        )
        if positive_cells:
            for position, score in positive_cells.items():
                updated = self._apply_positive_evidence(
                    updated,
                    position=position,
                    strength=positive_gain * score,
                )
        self.values = updated
        self.normalize()

    @staticmethod
    def update_values(
        values: np.ndarray,
        scanned_cells: Iterable[Position],
        positive_cells: dict[Position, float] | None = None,
        suppression: float = 0.2,
        positive_gain: float = 1.6,
        search_counts: dict[Position, int] | None = None,
    ) -> np.ndarray:
        updated = ProbabilityMap.suppress_values(
            values,
            searched_cells=scanned_cells,
            suppression=suppression,
            search_counts=search_counts,
        )
        if positive_cells:
            for position, score in positive_cells.items():
                updated = BeliefState._apply_positive_evidence(
                    updated,
                    position=position,
                    strength=positive_gain * score,
                )
        total = float(updated.sum())
        if total > 0.0:
            updated /= total
        return updated

    def entropy_map(self) -> np.ndarray:
        return self.entropy_map_values(self.values)

    def total_entropy(self) -> float:
        return float(self.entropy_map().sum())

    def expected_information_gain(
        self,
        environment: GridEnvironment,
        cells: Iterable[Position],
    ) -> float:
        entropy = self.entropy_map()
        return float(
            sum(
                entropy[y, x] * environment.get_detection_modifier((x, y))
                for x, y in cells
            )
        )

    @staticmethod
    def propagate_values(
        values: np.ndarray,
        environment: GridEnvironment,
        target_behavior: str,
        motion_strength: float,
    ) -> np.ndarray:
        behavior = target_behavior.lower()
        next_values = np.zeros_like(values)
        for position in environment.iter_traversable_cells():
            x, y = position
            neighbors = environment.get_neighbors(position, diagonal=True)
            candidates = neighbors + [position]
            weights = np.array(
                [
                    BeliefState._transition_weight(environment, candidate, behavior)
                    for candidate in candidates
                ],
                dtype=float,
            )
            weights = np.clip(weights, 1e-3, None)
            weights /= weights.sum()
            retained = values[y, x] * (1.0 - motion_strength)
            next_values[y, x] += retained
            propagated = values[y, x] * motion_strength
            for candidate, weight in zip(candidates, weights):
                cx, cy = candidate
                next_values[cy, cx] += propagated * weight
        next_values[environment.obstacle_mask] = 0.0
        total = float(next_values.sum())
        if total > 0.0:
            next_values /= total
        return next_values

    @staticmethod
    def entropy_map_values(values: np.ndarray) -> np.ndarray:
        clipped = np.clip(values, 1e-12, 1.0 - 1e-12)
        return -(clipped * np.log(clipped) + (1.0 - clipped) * np.log(1.0 - clipped))

    @staticmethod
    def _transition_weight(
        environment: GridEnvironment,
        candidate: Position,
        behavior: str,
    ) -> float:
        terrain = environment.terrain_at(candidate)
        move_weight = 1.0 / environment.get_movement_cost(candidate)
        concealment = max(1.2 - environment.get_detection_modifier(candidate), 0.2)
        trail_bonus = 1.5 if environment.has_trail(candidate) or terrain in (TerrainType.PLAIN, TerrainType.URBAN) else 0.8
        if behavior == "random_walk":
            return 1.0
        if behavior == "terrain_biased":
            return move_weight * concealment
        if behavior == "trail_biased":
            return move_weight * trail_bonus
        if behavior == "injured_slow":
            return move_weight * 1.15
        if behavior == "stationary_intervals":
            return move_weight * 0.9
        return move_weight * concealment

    @staticmethod
    def _apply_positive_evidence(
        values: np.ndarray,
        position: Position,
        strength: float,
    ) -> np.ndarray:
        updated = values.copy()
        x0, y0 = position
        y_indices, x_indices = np.indices(values.shape)
        squared_distance = (x_indices - x0) ** 2 + (y_indices - y0) ** 2
        boost = np.exp(-squared_distance / 4.0) * max(strength, 0.0)
        updated *= 1.0 + boost
        total = float(updated.sum())
        if total > 0.0:
            updated /= total
        return updated
