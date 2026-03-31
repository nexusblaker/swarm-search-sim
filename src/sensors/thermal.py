"""Thermal sensor model interfaces and default implementation."""

from __future__ import annotations

from dataclasses import dataclass
from math import dist
import math

import numpy as np

from src.agents.drone import Drone
from src.environment.grid import GridEnvironment
from src.simulation.sensing import (
    ContactSignal,
    INSPECTION_CONFIRMED,
    INSPECTION_PENDING,
    INSPECTION_REJECTED,
    InspectionOutcome,
    TrackedContact,
)


Position = tuple[int, int]


@dataclass(slots=True)
class ScanResult:
    """Result of a drone thermal scan."""

    detected: bool
    probability: float
    confidence: float
    false_positive: bool
    true_positive: bool
    scanned_cells: set[Position]
    candidate_scores: dict[Position, float]
    channel_scores: dict[str, float]
    contacts: list[ContactSignal]


class ThermalSensorModel:
    """Configurable thermal detection model with weather and terrain effects."""

    def __init__(
        self,
        false_positive_rate: float = 0.02,
        false_negative_rate: float = 0.08,
        visual_range_factor: float = 0.75,
        visual_false_positive_rate: float = 0.01,
        visual_false_negative_rate: float = 0.12,
        sensor_mode: str = "thermal_visual",
        weather_modifiers: dict[str, float] | None = None,
    ) -> None:
        self.false_positive_rate = false_positive_rate
        self.false_negative_rate = false_negative_rate
        self.visual_range_factor = visual_range_factor
        self.visual_false_positive_rate = visual_false_positive_rate
        self.visual_false_negative_rate = visual_false_negative_rate
        self.sensor_mode = sensor_mode
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

        distance_factor = 0.15 + 0.85 * max(0.0, 1.0 - distance / max(sensor_range, 1e-6))
        weather_factor = self.weather_modifiers.get(weather, 0.85)
        probability = distance_factor * terrain_modifier * weather_factor
        probability *= 1.0 - self.false_negative_rate
        return float(np.clip(probability, 0.0, 1.0))

    def _weather_factor(self, weather: str) -> float:
        return float(self.weather_modifiers.get(weather, 0.85))

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
        weather_factor = self._weather_factor(weather)
        distance = dist(drone.position, target_position)
        probability = self.detection_probability(
            drone_position=drone.position,
            target_position=target_position,
            terrain_modifier=terrain_modifier,
            weather=weather,
            sensor_range=drone.sensor_range,
        )
        scanned_cells = self._visible_cells(drone, environment)
        target_visible = target_position in scanned_cells
        visual_probability = self._visual_detection_probability(
            drone=drone,
            target_position=target_position,
            environment=environment,
            weather=weather,
        )
        thermal_hit = target_visible and rng.random() < probability
        visual_hit = (
            self.sensor_mode != "thermal_only"
            and target_visible
            and rng.random() < visual_probability
        )
        candidate_scores: dict[Position, float] = {}
        channel_scores = {"thermal": probability, "visual": visual_probability}
        true_detection = thermal_hit or visual_hit
        false_positive = False
        contacts: list[ContactSignal] = []

        false_positive_rate = self.false_positive_rate / max(
            weather_factor,
            0.25,
        )
        if true_detection and target_visible:
            blended_confidence = 0.65 * (probability if thermal_hit else 0.0)
            blended_confidence += 0.35 * (visual_probability if visual_hit else 0.0)
            candidate_score = max(0.12, blended_confidence)
            candidate_scores[target_position] = candidate_score
            note = (
                "Possible thermal contact detected at long range."
                if blended_confidence < 0.58 or distance >= drone.sensor_range * 0.62
                else "Strong contact detected and ready for close inspection."
            )
            contacts.append(
                ContactSignal(
                    position=target_position,
                    confidence=float(np.clip(blended_confidence, 0.0, 1.0)),
                    candidate_score=float(np.clip(candidate_score, 0.0, 1.0)),
                    requires_inspection=True,
                    is_true_target=True,
                    false_positive=False,
                    distance=float(distance),
                    terrain_modifier=terrain_modifier,
                    weather_factor=weather_factor,
                    source_channels=channel_scores,
                    note=note,
                )
            )
        elif scanned_cells and rng.random() < max(false_positive_rate, self.visual_false_positive_rate):
            false_positive = True
            ordered_cells = sorted(scanned_cells)
            candidate_position = ordered_cells[int(rng.integers(0, len(ordered_cells)))]
            false_confidence = max(false_positive_rate, self.visual_false_positive_rate)
            candidate_scores[candidate_position] = false_confidence
            true_detection = True
            contacts.append(
                ContactSignal(
                    position=candidate_position,
                    confidence=float(np.clip(false_confidence, 0.0, 1.0)),
                    candidate_score=float(np.clip(false_confidence, 0.0, 1.0)),
                    requires_inspection=True,
                    is_true_target=False,
                    false_positive=True,
                    distance=float(dist(drone.position, candidate_position)),
                    terrain_modifier=environment.get_detection_modifier(candidate_position),
                    weather_factor=weather_factor,
                    source_channels=channel_scores,
                    note="Low-confidence contact requires inspection.",
                )
            )

        confidence = probability if not false_positive else false_positive_rate
        return ScanResult(
            detected=true_detection,
            probability=probability,
            confidence=float(confidence),
            false_positive=false_positive,
            true_positive=bool(true_detection and not false_positive and target_visible),
            scanned_cells=scanned_cells,
            candidate_scores=candidate_scores,
            channel_scores=channel_scores,
            contacts=contacts,
        )

    def inspect_contact(
        self,
        drone: Drone,
        contact: TrackedContact,
        environment: GridEnvironment,
        weather: str,
        rng: np.random.Generator,
    ) -> InspectionOutcome:
        """Attempt to confirm or reject a tracked contact from a closer vantage."""

        distance = dist(drone.position, contact.position)
        terrain_modifier = environment.get_detection_modifier(contact.position)
        weather_factor = self._weather_factor(weather)
        line_of_sight = environment.has_line_of_sight(drone.position, contact.position)
        inspect_range = max(1.5, drone.sensor_range * 0.45)
        proximity = max(0.0, 1.0 - distance / max(inspect_range, 1e-6))
        visibility_score = terrain_modifier * weather_factor * (1.0 if line_of_sight else 0.55)

        if contact.is_true_target:
            confirm_probability = 0.48 + 0.34 * visibility_score + 0.22 * proximity
            confirm_probability += 0.1 * min(contact.inspection_attempts, 2)
            confirm_probability = float(np.clip(confirm_probability, 0.2, 0.99))
            if distance <= inspect_range and (rng.random() < confirm_probability or contact.inspection_attempts >= 1):
                return InspectionOutcome(
                    outcome=INSPECTION_CONFIRMED,
                    confidence=confirm_probability,
                    distance=float(distance),
                    note="Target confirmed after close inspection.",
                )
            return InspectionOutcome(
                outcome=INSPECTION_PENDING,
                confidence=confirm_probability,
                distance=float(distance),
                note="Inspection pass completed but more evidence is needed.",
            )

        reject_probability = 0.52 + 0.25 * proximity + 0.18 * (1.0 - min(terrain_modifier, 1.0))
        reject_probability += 0.1 * min(contact.inspection_attempts, 2)
        reject_probability = float(np.clip(reject_probability, 0.35, 0.99))
        if distance <= inspect_range and (rng.random() < reject_probability or contact.inspection_attempts >= 1):
            return InspectionOutcome(
                outcome=INSPECTION_REJECTED,
                confidence=reject_probability,
                distance=float(distance),
                note="Contact rejected after close inspection.",
            )
        return InspectionOutcome(
            outcome=INSPECTION_PENDING,
            confidence=reject_probability,
            distance=float(distance),
            note="Inspection pass completed but the contact remains uncertain.",
        )

    @staticmethod
    def _visible_cells(drone: Drone, environment: GridEnvironment) -> set[Position]:
        """Return cells inside the drone sensor radius."""

        visible: set[Position] = set()
        sensor_radius_sq = drone.sensor_range**2
        x0, y0 = drone.position
        heading = drone.heading if drone.heading != (0, 0) else (0, 1)
        heading_angle = math.atan2(heading[1], heading[0])
        half_fov = math.radians(drone.fov / 2.0)
        min_x = max(0, int(x0 - drone.sensor_range))
        max_x = min(environment.width - 1, int(x0 + drone.sensor_range))
        min_y = max(0, int(y0 - drone.sensor_range))
        max_y = min(environment.height - 1, int(y0 + drone.sensor_range))

        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                candidate = (x, y)
                if environment.is_obstacle(candidate):
                    continue
                if (x - x0) ** 2 + (y - y0) ** 2 > sensor_radius_sq:
                    continue
                if candidate != drone.position:
                    angle = math.atan2(y - y0, x - x0)
                    delta = math.atan2(
                        math.sin(angle - heading_angle),
                        math.cos(angle - heading_angle),
                    )
                    if abs(delta) > half_fov:
                        continue
                if environment.has_line_of_sight(drone.position, candidate):
                    visible.add(candidate)
        return visible

    def _visual_detection_probability(
        self,
        drone: Drone,
        target_position: Position,
        environment: GridEnvironment,
        weather: str,
    ) -> float:
        effective_range = drone.sensor_range * self.visual_range_factor
        terrain_modifier = min(1.0, environment.get_detection_modifier(target_position) + 0.1)
        weather_factor = self.weather_modifiers.get(weather, 0.85) * 0.9
        distance = dist(drone.position, target_position)
        if distance > effective_range:
            return 0.0
        probability = (1.0 - distance / max(effective_range, 1e-6)) * terrain_modifier * weather_factor
        probability *= 1.0 - self.visual_false_negative_rate
        return float(np.clip(probability, 0.0, 1.0))
