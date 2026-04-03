"""User-facing search pattern selection, geometry, and execution helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil, sqrt
from typing import Any

import numpy as np

from src.agents.drone import Drone
from src.environment.grid import GridEnvironment
from src.scenarios.scenario import ScenarioConfig


Position = tuple[int, int]

SEARCH_PATTERN_AUTO = "auto"
SEARCH_PATTERN_BROAD_SWEEP = "broad_area_sweep"
SEARCH_PATTERN_SECTOR_SPLIT = "sector_split"
SEARCH_PATTERN_EXPANDING_RING = "expanding_ring"
SEARCH_PATTERN_PERIMETER = "perimeter_containment"
SEARCH_PATTERN_ADAPTIVE = "adaptive_rebalance"

SEARCH_PATTERN_ORDER = [
    SEARCH_PATTERN_BROAD_SWEEP,
    SEARCH_PATTERN_SECTOR_SPLIT,
    SEARCH_PATTERN_EXPANDING_RING,
    SEARCH_PATTERN_PERIMETER,
    SEARCH_PATTERN_ADAPTIVE,
]

PATTERN_LABELS: dict[str, str] = {
    SEARCH_PATTERN_AUTO: "System recommended",
    SEARCH_PATTERN_BROAD_SWEEP: "Broad Area Sweep",
    SEARCH_PATTERN_SECTOR_SPLIT: "Sector Split",
    SEARCH_PATTERN_EXPANDING_RING: "Expanding Ring",
    SEARCH_PATTERN_PERIMETER: "Perimeter Containment",
    SEARCH_PATTERN_ADAPTIVE: "Adaptive Rebalance",
}

PATTERN_BRIEFS: dict[str, str] = {
    SEARCH_PATTERN_BROAD_SWEEP: "Spreads the fleet across evenly spaced lanes to maximize early area coverage.",
    SEARCH_PATTERN_SECTOR_SPLIT: "Divides the search box into independent sectors for parallel coverage and easier monitoring.",
    SEARCH_PATTERN_EXPANDING_RING: "Starts near the most likely origin area and grows outward over time.",
    SEARCH_PATTERN_PERIMETER: "Prioritizes the outer boundary to reduce the chance of missing movement beyond the search box.",
    SEARCH_PATTERN_ADAPTIVE: "Begins with structured coverage, then shifts drones toward clues, inspections, and under-covered sectors.",
}

PATTERN_FIT_SUMMARIES: dict[str, str] = {
    SEARCH_PATTERN_BROAD_SWEEP: "Best when the location is uncertain and early coverage matters most.",
    SEARCH_PATTERN_SECTOR_SPLIT: "Best when several drones can search in parallel without crowding each other.",
    SEARCH_PATTERN_EXPANDING_RING: "Best when the last known area is credible and the search should build outward.",
    SEARCH_PATTERN_PERIMETER: "Best when containment and boundary watch matter more than a point-focused search.",
    SEARCH_PATTERN_ADAPTIVE: "Best when the mission is likely to rebalance around cues, inspections, or rotating assets.",
}

PATTERN_INTENT_LABELS: dict[str, str] = {
    "broad_area_coverage": "broad area coverage",
    "fast_containment": "fast containment",
    "high_confidence_confirmation": "high-confidence confirmation",
    "battery_conservative": "battery-conservative search",
}


@dataclass(slots=True)
class SearchPatternGeometry:
    """Geometry assumptions used to explain and execute a pattern."""

    area_cells: int
    effective_swath_cells: float
    lane_spacing_cells: float
    overlap_margin: float
    sector_rows: int
    sector_cols: int
    sector_count: int
    ring_step_cells: int
    perimeter_spacing_cells: int
    coverage_depth: str
    technical_summary: dict[str, Any] = field(default_factory=dict)

    def operator_summary(self, pattern: str, drone_count: int) -> str:
        if pattern == SEARCH_PATTERN_BROAD_SWEEP:
            return (
                f"The fleet will move through evenly spaced lanes with about {self._fmt(self.lane_spacing_cells)} "
                f"cells between passes so early coverage stays broad instead of clustering on one point."
            )
        if pattern == SEARCH_PATTERN_SECTOR_SPLIT:
            return (
                f"The area is split into {self.sector_count} working sector"
                f"{'' if self.sector_count == 1 else 's'} so {drone_count} drone"
                f"{'' if drone_count == 1 else 's'} can search in parallel with clearer ownership."
            )
        if pattern == SEARCH_PATTERN_EXPANDING_RING:
            return (
                f"The search starts near the last known area and grows outward in about "
                f"{self.ring_step_cells}-cell ring steps as confidence falls away from the origin."
            )
        if pattern == SEARCH_PATTERN_PERIMETER:
            return (
                f"The fleet will trace the boundary with roughly {self.perimeter_spacing_cells}-cell spacing so the "
                "outer edge stays under watch while the interior remains visible."
            )
        return (
            f"The mission starts with structured coverage using about {self._fmt(self.lane_spacing_cells)}-cell spacing, "
            "then shifts assets toward clues, inspections, or thinner coverage when needed."
        )

    @staticmethod
    def _fmt(value: float) -> str:
        return f"{value:.1f}".rstrip("0").rstrip(".")


@dataclass(slots=True)
class SearchPatternDecision:
    """Pattern recommendation and explanation for operators."""

    pattern: str
    label: str
    summary: str
    reason: str
    fit_summary: str
    geometry: SearchPatternGeometry
    alternative_pattern: str | None = None
    alternative_label: str | None = None
    alternative_reason: str | None = None
    scores: dict[str, float] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return {
            "search_pattern": self.pattern,
            "search_pattern_label": self.label,
            "search_pattern_summary": self.summary,
            "search_pattern_reason": self.reason,
            "search_pattern_fit_summary": self.fit_summary,
            "search_pattern_alternative": self.alternative_pattern,
            "search_pattern_alternative_label": self.alternative_label,
            "search_pattern_alternative_reason": self.alternative_reason,
            "search_pattern_geometry": {
                **self.geometry.technical_summary,
                "area_cells": self.geometry.area_cells,
                "effective_swath_cells": round(self.geometry.effective_swath_cells, 2),
                "lane_spacing_cells": round(self.geometry.lane_spacing_cells, 2),
                "overlap_margin": round(self.geometry.overlap_margin, 3),
                "sector_rows": self.geometry.sector_rows,
                "sector_cols": self.geometry.sector_cols,
                "sector_count": self.geometry.sector_count,
                "ring_step_cells": self.geometry.ring_step_cells,
                "perimeter_spacing_cells": self.geometry.perimeter_spacing_cells,
                "coverage_depth": self.geometry.coverage_depth,
            },
        }


@dataclass(slots=True)
class SearchPatternState:
    """Live pattern state for execution and operator display."""

    base_pattern: str
    active_pattern: str
    label: str
    summary: str
    reason: str
    fit_summary: str
    geometry: SearchPatternGeometry
    rebalanced: bool = False
    rebalance_reason: str | None = None
    base_label: str | None = None

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "search_pattern": self.active_pattern,
            "search_pattern_label": self.label,
            "search_pattern_summary": self.summary,
            "search_pattern_reason": self.reason,
            "search_pattern_fit_summary": self.fit_summary,
            "search_pattern_base": self.base_pattern,
            "search_pattern_base_label": self.base_label or pattern_label(self.base_pattern),
            "search_pattern_rebalanced": self.rebalanced,
            "search_pattern_rebalance_reason": self.rebalance_reason,
            "search_pattern_geometry": {
                **self.geometry.technical_summary,
                "area_cells": self.geometry.area_cells,
                "effective_swath_cells": round(self.geometry.effective_swath_cells, 2),
                "lane_spacing_cells": round(self.geometry.lane_spacing_cells, 2),
                "overlap_margin": round(self.geometry.overlap_margin, 3),
                "sector_rows": self.geometry.sector_rows,
                "sector_cols": self.geometry.sector_cols,
                "sector_count": self.geometry.sector_count,
                "ring_step_cells": self.geometry.ring_step_cells,
                "perimeter_spacing_cells": self.geometry.perimeter_spacing_cells,
                "coverage_depth": self.geometry.coverage_depth,
            },
        }


def pattern_label(pattern: str | None) -> str:
    """Return an operator-facing pattern label."""

    if not pattern:
        return PATTERN_LABELS[SEARCH_PATTERN_AUTO]
    return PATTERN_LABELS.get(pattern, pattern.replace("_", " ").title())


def pattern_brief(pattern: str | None) -> str:
    """Return a short operator-facing pattern description."""

    if not pattern:
        return PATTERN_BRIEFS[SEARCH_PATTERN_BROAD_SWEEP]
    return PATTERN_BRIEFS.get(pattern, pattern_label(pattern))


def recommend_search_pattern(
    config: ScenarioConfig,
    fleet: dict[str, Any] | None = None,
    environment: GridEnvironment | None = None,
) -> SearchPatternDecision:
    """Recommend an operator-facing pattern from mission context."""

    geometry = estimate_search_geometry(config, fleet=fleet, environment=environment)
    explicit_pattern = (config.search_pattern or SEARCH_PATTERN_AUTO).lower()
    scores = _pattern_scores(config, geometry, fleet=fleet)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    default_pattern = ranked[0][0] if ranked else SEARCH_PATTERN_BROAD_SWEEP
    selected_pattern = explicit_pattern if explicit_pattern != SEARCH_PATTERN_AUTO else default_pattern
    alternative_pattern = next(
        (pattern for pattern, _ in ranked if pattern != selected_pattern),
        None,
    )
    summary = pattern_brief(selected_pattern)
    reason = _pattern_reason(selected_pattern, config, geometry)
    fit_summary = _pattern_fit_summary(selected_pattern, config, geometry)
    alternative_reason = _pattern_reason(alternative_pattern, config, geometry) if alternative_pattern else None
    return SearchPatternDecision(
        pattern=selected_pattern,
        label=pattern_label(selected_pattern),
        summary=summary,
        reason=reason,
        fit_summary=fit_summary,
        geometry=geometry,
        alternative_pattern=alternative_pattern,
        alternative_label=pattern_label(alternative_pattern) if alternative_pattern else None,
        alternative_reason=alternative_reason,
        scores={pattern: round(score, 2) for pattern, score in ranked},
    )


def estimate_search_geometry(
    config: ScenarioConfig,
    fleet: dict[str, Any] | None = None,
    environment: GridEnvironment | None = None,
) -> SearchPatternGeometry:
    """Estimate operator-readable coverage geometry from mission context."""

    width, height = config.map_size
    area_cells = width * height
    mission_area = config.mission_area or {}
    terrain_summary = mission_area.get("terrain_summary", {})
    weather_factor = float(config.weather_modifiers.get(config.weather, 1.0))
    scenario_visibility = {
        "open_terrain": 1.0,
        "mixed_terrain": 0.9,
        "dense_forest": 0.68,
        "obstacle_heavy": 0.78,
        "poor_comms": 0.88,
        "layered_demo": 0.82,
        "high_wind": 0.72,
    }.get(config.scenario_family, 0.86)
    environment_visibility = scenario_visibility
    if environment is not None:
        traversable = list(environment.iter_traversable_cells())
        if traversable:
            environment_visibility = float(
                np.mean([environment.get_detection_modifier(position) for position in traversable])
            )
    fleet = fleet or {}
    sensor_mode_factor = 1.08 if config.sensor_mode == "thermal_visual" else 1.0
    fleet_coverage = float(fleet.get("coverage_score") or 1.0)
    slope_factor = {
        "light": 1.0,
        "moderate": 0.93,
        "elevated": 0.86,
    }.get(str(terrain_summary.get("slope_burden")), 1.0)
    trail_factor = {
        "good": 1.05,
        "workable": 1.0,
        "limited": 0.94,
    }.get(str(terrain_summary.get("trail_access")), 1.0)
    obstacle_factor = max(0.82, 1.0 - float(terrain_summary.get("obstacle_coverage_pct", 0.0)) * 0.45)
    base_swath = max(2.0, config.sensor_range * (1.45 if config.fov >= 110.0 else 1.25))
    effective_swath = max(
        1.2,
        base_swath
        * weather_factor
        * ((scenario_visibility + environment_visibility) / 2.0)
        * sensor_mode_factor
        * fleet_coverage
        * slope_factor
        * trail_factor
        * obstacle_factor,
    )
    overlap_margin = max(0.08, min(0.36, _effective_overlap_margin(config)))
    lane_spacing = max(1.0, effective_swath * (1.0 - overlap_margin))
    sector_cols = max(1, round(sqrt(max(config.num_drones, 1) * max(width, 1) / max(height, 1))))
    sector_rows = max(1, ceil(max(config.num_drones, 1) / sector_cols))
    sector_count = max(config.num_drones, sector_rows * sector_cols)
    ring_step = max(2, int(round(max(1.0, lane_spacing * 0.8))))
    perimeter_spacing = max(2, int(round(lane_spacing)))
    coverage_depth = (
        "broad"
        if lane_spacing >= 5.0
        else "balanced"
        if lane_spacing >= 3.0
        else "tight"
    )
    return SearchPatternGeometry(
        area_cells=area_cells,
        effective_swath_cells=effective_swath,
        lane_spacing_cells=lane_spacing,
        overlap_margin=overlap_margin,
        sector_rows=sector_rows,
        sector_cols=sector_cols,
        sector_count=sector_count,
        ring_step_cells=ring_step,
        perimeter_spacing_cells=perimeter_spacing,
        coverage_depth=coverage_depth,
        technical_summary={
            "weather_factor": round(weather_factor, 3),
            "visibility_modifier": round((scenario_visibility + environment_visibility) / 2.0, 3),
            "sensor_mode_factor": round(sensor_mode_factor, 3),
            "fleet_coverage_factor": round(fleet_coverage, 3),
            "area_sq_km": round(float(mission_area.get("area_sq_km", 0.0)), 2),
            "shape_ratio": round(float(mission_area.get("shape_ratio", 1.0)), 2),
            "staging_distance_to_center_km": round(float(mission_area.get("staging_distance_to_center_km", 0.0)), 2),
            "slope_burden": terrain_summary.get("slope_burden"),
            "dominant_terrain": terrain_summary.get("dominant_terrain"),
        },
    )


class SearchPatternPlanner:
    """Translate operator-facing search patterns into stable goal assignments."""

    def __init__(self, config: ScenarioConfig, environment: GridEnvironment) -> None:
        self.config = config
        self.environment = environment
        self.base_decision = recommend_search_pattern(config, environment=environment)
        self.base_pattern = self.base_decision.pattern
        self.geometry = self.base_decision.geometry
        self.route_sequences: dict[int, list[Position]] = {}
        self.route_indexes: dict[int, int] = {}
        self.pending_events: list[dict[str, Any]] = [
            {
                "event_type": "search_pattern_selected",
                "pattern": self.base_pattern,
                "pattern_label": self.base_decision.label,
                "summary": self.base_decision.summary,
                "reason": self.base_decision.reason,
            }
        ]
        self.current_state = SearchPatternState(
            base_pattern=self.base_pattern,
            active_pattern=self.base_pattern,
            label=self.base_decision.label,
            summary=self.base_decision.summary,
            reason=self.base_decision.reason,
            fit_summary=self.base_decision.fit_summary,
            geometry=self.geometry,
            rebalanced=False,
            rebalance_reason=None,
            base_label=self.base_decision.label,
        )

    def prepare(self, drones: list[Drone]) -> None:
        """Build stable route sequences for the current fleet."""

        self.route_sequences = self._build_routes(drones)
        self.route_indexes = {drone.id: 0 for drone in drones}

    def select_goals(
        self,
        drones: list[Drone],
        probability_map: Any,
        tracked_contacts: list[dict[str, Any]],
        coverage_gap_active: bool,
    ) -> dict[int, Position]:
        """Return pattern-aware goals for active drones."""

        goals: dict[int, Position] = {}
        if not self.route_sequences:
            self.prepare(drones)

        rebalance_reason = self._rebalance_reason(drones, tracked_contacts, coverage_gap_active)
        active_pattern = SEARCH_PATTERN_ADAPTIVE if rebalance_reason else self.base_pattern
        if active_pattern != self.current_state.active_pattern or rebalance_reason != self.current_state.rebalance_reason:
            event_type = "search_pattern_rebalanced" if rebalance_reason else "search_pattern_restored"
            summary = (
                self._adaptive_summary(rebalance_reason)
                if rebalance_reason
                else self.base_decision.summary
            )
            self.pending_events.append(
                {
                    "event_type": event_type,
                    "pattern": active_pattern,
                    "pattern_label": pattern_label(active_pattern),
                    "base_pattern": self.base_pattern,
                    "base_pattern_label": self.base_decision.label,
                    "reason": rebalance_reason,
                    "summary": summary,
                }
            )
        self.current_state = SearchPatternState(
            base_pattern=self.base_pattern,
            active_pattern=active_pattern,
            label=pattern_label(active_pattern),
            summary=self._adaptive_summary(rebalance_reason) if rebalance_reason else self.base_decision.summary,
            reason=self._adaptive_reason(rebalance_reason) if rebalance_reason else self.base_decision.reason,
            fit_summary=self.base_decision.fit_summary,
            geometry=self.geometry,
            rebalanced=bool(rebalance_reason),
            rebalance_reason=rebalance_reason,
            base_label=self.base_decision.label,
        )

        if active_pattern == SEARCH_PATTERN_ADAPTIVE and rebalance_reason:
            return self._adaptive_goals(drones, probability_map, tracked_contacts, goals)

        for drone in drones:
            route = self.route_sequences.get(drone.id, [drone.position])
            if not route:
                goals[drone.id] = drone.position
                continue
            index = self.route_indexes.get(drone.id, 0)
            if index >= len(route):
                index = 0
            current_target = route[index]
            if self._distance(drone.position, current_target) <= 1.0 and len(route) > 1:
                index = (index + 1) % len(route)
                self.route_indexes[drone.id] = index
                current_target = route[index]
            goals[drone.id] = current_target
        return goals

    def state_snapshot(self) -> dict[str, Any]:
        """Return the current operator-facing pattern state."""

        return self.current_state.to_snapshot()

    def drain_events(self) -> list[dict[str, Any]]:
        """Return and clear pending pattern events."""

        events = list(self.pending_events)
        self.pending_events = []
        return events

    def _build_routes(self, drones: list[Drone]) -> dict[int, list[Position]]:
        if self.base_pattern == SEARCH_PATTERN_BROAD_SWEEP:
            return self._broad_sweep_routes(drones)
        if self.base_pattern == SEARCH_PATTERN_SECTOR_SPLIT:
            return self._sector_routes(drones)
        if self.base_pattern == SEARCH_PATTERN_EXPANDING_RING:
            return self._expanding_ring_routes(drones)
        if self.base_pattern == SEARCH_PATTERN_PERIMETER:
            return self._perimeter_routes(drones)
        return self._adaptive_base_routes(drones)

    def _adaptive_base_routes(self, drones: list[Drone]) -> dict[int, list[Position]]:
        if self.config.last_known_status == "known":
            return self._expanding_ring_routes(drones)
        return self._broad_sweep_routes(drones)

    def _broad_sweep_routes(
        self,
        drones: list[Drone],
        *,
        bounds: tuple[int, int, int, int] | None = None,
    ) -> dict[int, list[Position]]:
        min_x, max_x, min_y, max_y = bounds or (0, self.environment.width - 1, 0, self.environment.height - 1)
        lane_spacing = max(1, int(round(self.geometry.lane_spacing_cells)))
        lane_xs = list(range(min_x, max_x + 1, lane_spacing))
        if len(lane_xs) < len(drones):
            lane_xs = list(np.linspace(min_x, max_x, num=max(len(drones), 1), dtype=int))
        routes: dict[int, list[Position]] = {}
        for index, drone in enumerate(drones):
            assigned = lane_xs[index:: max(len(drones), 1)] or [lane_xs[index % max(len(lane_xs), 1)]]
            route: list[Position] = []
            for lane_index, lane_x in enumerate(assigned):
                top = self._nearest_open((lane_x, min_y))
                bottom = self._nearest_open((lane_x, max_y))
                if lane_index % 2 == 0:
                    route.extend([top, bottom])
                else:
                    route.extend([bottom, top])
            routes[drone.id] = self._dedupe(route)
        return routes

    def _sector_routes(self, drones: list[Drone]) -> dict[int, list[Position]]:
        bounds = self._sector_bounds(len(drones))
        routes: dict[int, list[Position]] = {}
        for drone, sector in zip(drones, bounds):
            routes[drone.id] = self._broad_sweep_routes([drone], bounds=sector)[drone.id]
        return routes

    def _sector_bounds(self, count: int) -> list[tuple[int, int, int, int]]:
        width, height = self.environment.width, self.environment.height
        cols = max(1, self.geometry.sector_cols)
        rows = max(1, self.geometry.sector_rows)
        x_edges = np.linspace(0, width - 1, num=cols + 1, dtype=int)
        y_edges = np.linspace(0, height - 1, num=rows + 1, dtype=int)
        bounds: list[tuple[int, int, int, int]] = []
        for row in range(rows):
            for col in range(cols):
                min_x = int(x_edges[col])
                max_x = int(x_edges[col + 1])
                min_y = int(y_edges[row])
                max_y = int(y_edges[row + 1])
                bounds.append((min_x, max_x, min_y, max_y))
        return bounds[: max(count, 1)]

    def _expanding_ring_routes(self, drones: list[Drone]) -> dict[int, list[Position]]:
        center = self._nearest_open(self.config.last_known_position)
        max_radius = max(self.environment.width, self.environment.height)
        step = max(1, self.geometry.ring_step_cells)
        ring_points: list[Position] = []
        for radius in range(0, max_radius + 1, step):
            candidates = [
                (center[0] - radius, center[1] - radius),
                (center[0], center[1] - radius),
                (center[0] + radius, center[1] - radius),
                (center[0] + radius, center[1]),
                (center[0] + radius, center[1] + radius),
                (center[0], center[1] + radius),
                (center[0] - radius, center[1] + radius),
                (center[0] - radius, center[1]),
            ]
            for candidate in candidates:
                if self.environment.in_bounds(candidate):
                    ring_points.append(self._nearest_open(candidate))
        ring_points = self._dedupe([center] + ring_points)
        routes: dict[int, list[Position]] = {}
        for index, drone in enumerate(drones):
            route = ring_points[index:: max(len(drones), 1)] or [center]
            routes[drone.id] = route
        return routes

    def _perimeter_routes(self, drones: list[Drone]) -> dict[int, list[Position]]:
        width, height = self.environment.width, self.environment.height
        spacing = max(1, self.geometry.perimeter_spacing_cells)
        perimeter: list[Position] = []
        for x in range(0, width, spacing):
            perimeter.append((x, 0))
        for y in range(0, height, spacing):
            perimeter.append((width - 1, y))
        for x in range(width - 1, -1, -spacing):
            perimeter.append((x, height - 1))
        for y in range(height - 1, -1, -spacing):
            perimeter.append((0, y))
        perimeter = self._dedupe(
            [
                self._nearest_open(position)
                for position in perimeter
                if self.environment.in_bounds(position)
            ]
        )
        routes: dict[int, list[Position]] = {}
        for index, drone in enumerate(drones):
            routes[drone.id] = perimeter[index:: max(len(drones), 1)] or [self._nearest_open(drone.position)]
        return routes

    def _adaptive_goals(
        self,
        drones: list[Drone],
        probability_map: Any,
        tracked_contacts: list[dict[str, Any]],
        fallback: dict[int, Position],
    ) -> dict[int, Position]:
        contact_positions = [
            tuple(contact.get("position", (0, 0)))
            for contact in tracked_contacts
            if not bool(contact.get("resolved"))
        ]
        if contact_positions:
            anchor = self._nearest_open(contact_positions[0])
            support_points = self._support_ring(anchor)
            goals: dict[int, Position] = {}
            for index, drone in enumerate(drones):
                if index == 0:
                    goals[drone.id] = anchor
                else:
                    goals[drone.id] = support_points[(index - 1) % len(support_points)]
            return goals

        if probability_map is not None:
            values = getattr(probability_map, "values", probability_map)
            ranked = np.dstack(np.unravel_index(np.argsort(values.ravel())[::-1], values.shape))[0]
            goals = {}
            used: set[Position] = set()
            for drone in drones:
                for row, col in ranked:
                    candidate = self._nearest_open((int(col), int(row)))
                    if candidate in used:
                        continue
                    used.add(candidate)
                    goals[drone.id] = candidate
                    break
                goals.setdefault(drone.id, drone.position)
            return goals
        return fallback

    def _support_ring(self, anchor: Position) -> list[Position]:
        spacing = max(1, int(round(self.geometry.lane_spacing_cells / 2.0)))
        offsets = [
            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1),
            (1, 1),
            (1, -1),
            (-1, 1),
            (-1, -1),
        ]
        points = []
        for dx, dy in offsets:
            candidate = (anchor[0] + dx * spacing, anchor[1] + dy * spacing)
            points.append(self._nearest_open(candidate))
        return self._dedupe(points) or [anchor]

    def _nearest_open(self, preferred: Position) -> Position:
        if self.environment.in_bounds(preferred) and not self.environment.is_obstacle(preferred):
            return preferred
        traversable = list(self.environment.iter_traversable_cells())
        return min(
            traversable,
            key=lambda position: abs(position[0] - preferred[0]) + abs(position[1] - preferred[1]),
        )

    def _rebalance_reason(
        self,
        drones: list[Drone],
        tracked_contacts: list[dict[str, Any]],
        coverage_gap_active: bool,
    ) -> str | None:
        if any(not bool(contact.get("resolved")) for contact in tracked_contacts):
            return "possible contact activity"
        active_search = sum(1 for drone in drones if drone.contributes_to_search)
        if coverage_gap_active:
            return "coverage thinned during asset rotation"
        if active_search < max(1, ceil(self.config.num_drones * 0.65)):
            return "the active fleet temporarily reduced"
        return None

    def _adaptive_summary(self, reason: str | None) -> str:
        if not reason:
            return self.base_decision.summary
        return f"{PATTERN_BRIEFS[SEARCH_PATTERN_ADAPTIVE]} The mission is currently tightening around {reason}."

    def _adaptive_reason(self, reason: str | None) -> str:
        if not reason:
            return self.base_decision.reason
        return (
            f"The mission started with {self.base_decision.label.lower()}, but it has shifted into adaptive rebalance "
            f"because {reason}."
        )

    @staticmethod
    def _distance(a: Position, b: Position) -> float:
        return float(np.hypot(a[0] - b[0], a[1] - b[1]))

    @staticmethod
    def _dedupe(points: list[Position]) -> list[Position]:
        unique: list[Position] = []
        for point in points:
            if not unique or unique[-1] != point:
                unique.append(point)
        return unique


def _pattern_scores(
    config: ScenarioConfig,
    geometry: SearchPatternGeometry,
    *,
    fleet: dict[str, Any] | None = None,
) -> dict[str, float]:
    fleet = fleet or {}
    width, height = config.map_size
    area_cells = width * height
    mixed_fleet = int(fleet.get("drone_type_count") or 1) > 1
    coverage = float(fleet.get("coverage_score") or 1.0)
    endurance = float(fleet.get("endurance_score") or 1.0)
    detection = float(fleet.get("detection_score") or 1.0)
    mission_area = config.mission_area or {}
    terrain_summary = mission_area.get("terrain_summary", {})
    area_sq_km = float(mission_area.get("area_sq_km", 0.0))
    shape_ratio = float(mission_area.get("shape_ratio", 1.0))
    staging_distance = float(mission_area.get("staging_distance_to_center_km", 0.0))
    width_km = float(mission_area.get("width_km", 0.0))
    height_km = float(mission_area.get("height_km", 0.0))
    slope_burden = str(terrain_summary.get("slope_burden", ""))
    dominant_terrain = str(terrain_summary.get("dominant_terrain", ""))
    unknown_lkp = config.last_known_status == "unknown"
    large_area = area_cells >= 300
    very_large_area = area_cells >= 500
    known_origin = not unknown_lkp
    mission_intent = config.mission_intent

    scores = {
        SEARCH_PATTERN_BROAD_SWEEP: 0.0,
        SEARCH_PATTERN_SECTOR_SPLIT: 0.0,
        SEARCH_PATTERN_EXPANDING_RING: 0.0,
        SEARCH_PATTERN_PERIMETER: 0.0,
        SEARCH_PATTERN_ADAPTIVE: 0.0,
    }

    if unknown_lkp:
        scores[SEARCH_PATTERN_BROAD_SWEEP] += 7.0
        scores[SEARCH_PATTERN_SECTOR_SPLIT] += 4.5
        scores[SEARCH_PATTERN_EXPANDING_RING] -= 7.0
        scores[SEARCH_PATTERN_PERIMETER] += 3.0
        scores[SEARCH_PATTERN_ADAPTIVE] += 2.5
    if known_origin:
        scores[SEARCH_PATTERN_EXPANDING_RING] += 7.5
        scores[SEARCH_PATTERN_ADAPTIVE] += 3.0
    if large_area:
        scores[SEARCH_PATTERN_BROAD_SWEEP] += 3.5
        scores[SEARCH_PATTERN_SECTOR_SPLIT] += 3.0
        scores[SEARCH_PATTERN_PERIMETER] += 1.5
    if very_large_area:
        scores[SEARCH_PATTERN_EXPANDING_RING] -= 2.0
    if area_sq_km >= 35.0:
        scores[SEARCH_PATTERN_BROAD_SWEEP] += 3.0
        scores[SEARCH_PATTERN_SECTOR_SPLIT] += 2.5
    if shape_ratio >= 1.8:
        scores[SEARCH_PATTERN_BROAD_SWEEP] += 2.0
        scores[SEARCH_PATTERN_PERIMETER] += 1.8
    elif shape_ratio <= 1.2 and known_origin:
        scores[SEARCH_PATTERN_EXPANDING_RING] += 1.8
    if staging_distance > max(width_km, height_km, 1.0) * 0.3:
        scores[SEARCH_PATTERN_ADAPTIVE] += 2.2
        scores[SEARCH_PATTERN_SECTOR_SPLIT] += 1.4
    if slope_burden == "elevated":
        scores[SEARCH_PATTERN_ADAPTIVE] += 2.4
        scores[SEARCH_PATTERN_EXPANDING_RING] += 1.2
        scores[SEARCH_PATTERN_BROAD_SWEEP] -= 1.4
    if dominant_terrain in {"forest", "hill country"}:
        scores[SEARCH_PATTERN_ADAPTIVE] += 1.4
    if dominant_terrain == "water / no-go":
        scores[SEARCH_PATTERN_SECTOR_SPLIT] += 1.2
    if config.num_drones >= 5:
        scores[SEARCH_PATTERN_SECTOR_SPLIT] += 4.0
        scores[SEARCH_PATTERN_ADAPTIVE] += 2.0
    if config.num_drones <= 2:
        scores[SEARCH_PATTERN_EXPANDING_RING] += 2.5
        scores[SEARCH_PATTERN_SECTOR_SPLIT] -= 3.0
    if mixed_fleet:
        scores[SEARCH_PATTERN_ADAPTIVE] += 3.5
        scores[SEARCH_PATTERN_SECTOR_SPLIT] += 2.0
    if coverage >= 1.12:
        scores[SEARCH_PATTERN_BROAD_SWEEP] += 2.5
        scores[SEARCH_PATTERN_SECTOR_SPLIT] += 2.0
    if detection >= 1.08:
        scores[SEARCH_PATTERN_EXPANDING_RING] += 1.8
        scores[SEARCH_PATTERN_ADAPTIVE] += 1.5
    if endurance < 0.96:
        scores[SEARCH_PATTERN_ADAPTIVE] += 1.8
        scores[SEARCH_PATTERN_PERIMETER] -= 1.2
    if config.scenario_family == "dense_forest":
        scores[SEARCH_PATTERN_EXPANDING_RING] += 2.0
        scores[SEARCH_PATTERN_ADAPTIVE] += 1.8
        scores[SEARCH_PATTERN_BROAD_SWEEP] -= 1.5
    if config.scenario_family == "poor_comms":
        scores[SEARCH_PATTERN_SECTOR_SPLIT] += 2.0
    if config.weather in {"rain", "storm"}:
        scores[SEARCH_PATTERN_ADAPTIVE] += 2.0
        scores[SEARCH_PATTERN_EXPANDING_RING] += 1.0

    if mission_intent == "broad_area_coverage":
        scores[SEARCH_PATTERN_BROAD_SWEEP] += 5.0
        scores[SEARCH_PATTERN_SECTOR_SPLIT] += 3.5
    elif mission_intent == "fast_containment":
        scores[SEARCH_PATTERN_PERIMETER] += 6.0
        scores[SEARCH_PATTERN_SECTOR_SPLIT] += 2.5
    elif mission_intent == "high_confidence_confirmation":
        scores[SEARCH_PATTERN_EXPANDING_RING] += 4.5
        scores[SEARCH_PATTERN_ADAPTIVE] += 4.0
    elif mission_intent == "battery_conservative":
        scores[SEARCH_PATTERN_SECTOR_SPLIT] += 2.0
        scores[SEARCH_PATTERN_ADAPTIVE] += 3.5

    if config.strategy == "sector_search":
        scores[SEARCH_PATTERN_BROAD_SWEEP] += 2.5
        scores[SEARCH_PATTERN_SECTOR_SPLIT] += 2.5
    elif config.strategy == "auction_based":
        scores[SEARCH_PATTERN_PERIMETER] += 2.5
        scores[SEARCH_PATTERN_SECTOR_SPLIT] += 1.5
    elif config.strategy == "information_gain":
        scores[SEARCH_PATTERN_EXPANDING_RING] += 2.5
        scores[SEARCH_PATTERN_ADAPTIVE] += 2.0
    elif config.strategy == "probability_greedy":
        scores[SEARCH_PATTERN_ADAPTIVE] += 2.0
        scores[SEARCH_PATTERN_BROAD_SWEEP] += 1.0

    if geometry.coverage_depth == "tight":
        scores[SEARCH_PATTERN_EXPANDING_RING] += 1.0
        scores[SEARCH_PATTERN_ADAPTIVE] += 1.0
    elif geometry.coverage_depth == "broad":
        scores[SEARCH_PATTERN_BROAD_SWEEP] += 1.0

    return scores


def _pattern_reason(
    pattern: str | None,
    config: ScenarioConfig,
    geometry: SearchPatternGeometry,
) -> str:
    if pattern is None:
        return "No alternate pattern summary was generated."
    intent_label = PATTERN_INTENT_LABELS.get(config.mission_intent, config.mission_intent.replace("_", " "))
    area_context = _area_context_phrase(config.mission_area)
    if pattern == SEARCH_PATTERN_BROAD_SWEEP:
        return (
            "The last known position is uncertain and the search area is wide, so a coverage-first layout is the safest "
            f"way to support {intent_label} without over-focusing on a single point. {area_context}"
        )
    if pattern == SEARCH_PATTERN_SECTOR_SPLIT:
        return (
            "Several drones can cover ground in parallel here, so dividing the area into sectors makes the mission easier "
            f"to monitor while reducing redundant overlap. {area_context}"
        )
    if pattern == SEARCH_PATTERN_EXPANDING_RING:
        precision_phrase = (
            "A precise last known point is available"
            if (config.mission_area or {}).get("last_known_location")
            else "A credible last known area is available"
        )
        return (
            f"{precision_phrase}, so starting tight and expanding outward keeps the search anchored "
            f"around the best early clue. {area_context}"
        )
    if pattern == SEARCH_PATTERN_PERIMETER:
        return (
            "Containment is the stronger priority here, so keeping the boundary under watch reduces the chance of missing "
            f"movement beyond the search box. {area_context}"
        )
    return (
        f"The mission is likely to shift around clues, inspections, or rotating assets, so a flexible pattern is a better "
        f"fit than a fixed layout for {intent_label}. {area_context}"
    )


def _pattern_fit_summary(
    pattern: str,
    config: ScenarioConfig,
    geometry: SearchPatternGeometry,
) -> str:
    base = PATTERN_FIT_SUMMARIES.get(pattern, pattern_brief(pattern))
    area = config.mission_area or {}
    terrain_summary = area.get("terrain_summary", {})
    weather_summary = area.get("weather_summary", {})
    terrain_note = ""
    weather_note = ""
    if terrain_summary.get("dominant_terrain"):
        terrain_note = f" {terrain_summary['dominant_terrain'].title()} is the dominant ground type."
    if float(weather_summary.get("wind_speed_kph", 0.0) or 0.0) >= 24.0:
        weather_note = f" Winds near {float(weather_summary['wind_speed_kph']):.0f} kph are tightening spacing and reserve pacing."
    return (
        f"{base} Current spacing is built around an effective swath of about {geometry.effective_swath_cells:.1f} cells."
        f"{terrain_note}{weather_note}"
    )


def _effective_overlap_margin(config: ScenarioConfig) -> float:
    overlap = float(config.coverage_overlap_margin)
    if config.scenario_family == "dense_forest":
        overlap += 0.08
    if config.weather in {"rain", "storm"}:
        overlap += 0.05
    if config.mission_intent == "high_confidence_confirmation":
        overlap += 0.04
    if config.reserve_preset == "aggressive":
        overlap -= 0.03
    return overlap


def _area_context_phrase(mission_area: dict[str, Any] | None) -> str:
    if not mission_area:
        return ""
    location = str(mission_area.get("location_display_name") or "the selected area")
    width = float(mission_area.get("width_km", 0.0))
    height = float(mission_area.get("height_km", 0.0))
    staging_distance = float(mission_area.get("staging_distance_to_center_km", 0.0))
    terrain_summary = mission_area.get("terrain_summary", {})
    weather_summary = mission_area.get("weather_summary", {})
    terrain = str(terrain_summary.get("dominant_terrain") or "").strip()
    terrain_text = f" with mostly {terrain}" if terrain else ""
    staging_text = ""
    weather_text = ""
    precise_last_known_text = ""
    if staging_distance >= 0.5:
        staging_text = f" Staging sits about {staging_distance:.1f} km from the area centre."
    if float(weather_summary.get("wind_speed_kph", 0.0) or 0.0) >= 18.0:
        weather_text = (
            f" Current weather is {str(weather_summary.get('condition_label') or 'elevated wind').lower()}."
        )
    if mission_area.get("last_known_location"):
        precise_last_known_text = " A last known point has been placed inside the area."
    return (
        f"{location} spans about {width:.1f} by {height:.1f} km{terrain_text}."
        f"{staging_text}{weather_text}{precise_last_known_text}"
    ).strip()
