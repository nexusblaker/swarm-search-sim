"""Thermal sensor model interfaces and default implementation."""

from __future__ import annotations

from dataclasses import dataclass
from math import dist

import numpy as np

from src.agents.drone import Drone
from src.environment.grid import GridEnvironment


Position = tuple[int, int]


@dataclass(slots=True)
class ScanResult:
    """Result of a drone thermal scan."""

    detected: bool
    probability: float
    confidence: float
    false_positive: bool
    scanned_cells: set[Position]


class ThermalSensorModel:
    """Configurable thermal detection model with weather and terrain effects."""

    def __init__(
        self,
        false_positive_rate: float = 0.02,
        false_negative_rate: float = 0.08,
        weather_modifiers: dict[str, float] | None = None,
    ) -> None:
        self.false_positive_rate = false_positive_rate
        self.false_negative_rate = false_negative_rate
        self.weather_modifiers = weather_modifiers or {
            "clear": 1.0,
            "windy": 0.9,
            "rain": 0.75,
            "storm": 0.55,
        }

    def detection_probability(
        self,
        drone_position: Position,
        target_position: Position,
        terrain_modifier: float,
        weather: str,
        sensor_range: float,
    ) -> float:
        """Estimate target detection probability for a single scan."""

        distance = dist(drone_position, target_position)
        if distance > sensor_range:
            return 0.0

        distance_factor = max(0.0, 1.0 - distance / max(sensor_range, 1e-6))
        weather_factor = self.weather_modifiers.get(weather, 0.85)
        probability = distance_factor * terrain_modifier * weather_factor
        probability *= 1.0 - self.false_negative_rate
        return float(np.clip(probability, 0.0, 1.0))

    def scan(
        self,
        drone: Drone,
        target_position: Position,
        environment: GridEnvironment,
        weather: str,
        rng: np.random.Generator,
    ) -> ScanResult:
        """Scan the environment around a drone for the target."""

        terrain_modifier = environment.get_detection_modifier(target_position)
        probability = self.detection_probability(
            drone_position=drone.position,
            target_position=target_position,
            terrain_modifier=terrain_modifier,
            weather=weather,
            sensor_range=drone.sensor_range,
        )
        scanned_cells = self._visible_cells(drone, environment)
        true_detection = rng.random() < probability
        false_positive = False

        if not true_detection and rng.random() < self.false_positive_rate:
            true_detection = True
            false_positive = True

        confidence = probability if not false_positive else self.false_positive_rate
        return ScanResult(
            detected=true_detection,
            probability=probability,
            confidence=float(confidence),
            false_positive=false_positive,
            scanned_cells=scanned_cells,
        )

    @staticmethod
    def _visible_cells(drone: Drone, environment: GridEnvironment) -> set[Position]:
        """Return cells inside the drone sensor radius."""

        visible: set[Position] = set()
        sensor_radius_sq = drone.sensor_range**2
        x0, y0 = drone.position
        min_x = max(0, int(x0 - drone.sensor_range))
        max_x = min(environment.width - 1, int(x0 + drone.sensor_range))
        min_y = max(0, int(y0 - drone.sensor_range))
        max_y = min(environment.height - 1, int(y0 + drone.sensor_range))

        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                if (x - x0) ** 2 + (y - y0) ** 2 <= sensor_radius_sq and not environment.is_obstacle((x, y)):
                    visible.add((x, y))
        return visible
