"""Auction-based coordination strategy."""

from __future__ import annotations

from src.agents.drone import Drone
from src.coordination.base import BaseStrategy
from src.environment.grid import GridEnvironment
from src.probability.heatmap import ProbabilityMap


Position = tuple[int, int]


class AuctionBasedStrategy(BaseStrategy):
    """Assign high-value cells to drones through greedy bidding."""

    name = "auction_based"

    def select_moves(
        self,
        drones: list[Drone],
        environment: GridEnvironment,
        probability_map: ProbabilityMap,
        step_index: int,
    ) -> dict[int, Position]:
        active_drones = [drone for drone in drones if drone.is_operational]
        assignments: dict[int, Position] = {drone.id: drone.position for drone in drones}
        claimed_cells: set[Position] = set()

        candidate_cells: list[Position] = []
        for drone in active_drones:
            for candidate in self.top_candidate_cells_for_drone(
                drone,
                environment,
                probability_map,
                limit=10,
            ):
                if candidate not in candidate_cells:
                    candidate_cells.append(candidate)

        for drone in sorted(active_drones, key=lambda item: item.battery, reverse=True):
            best_cell = drone.position
            best_bid = float("-inf")
            for candidate in candidate_cells:
                if drone.comms_online and candidate in claimed_cells:
                    continue
                route_cost = self.route_cost(environment, drone.position, candidate)
                expected_value = self.belief_value(drone, probability_map, candidate) * 25.0
                battery_factor = max(drone.battery / max(drone.initial_battery, 1.0), 0.1)
                overlap_penalty = self.overlap_penalty(drone, candidate)
                bid = expected_value * battery_factor - 0.2 * route_cost - overlap_penalty
                if bid > best_bid:
                    best_bid = bid
                    best_cell = candidate
            if drone.comms_online:
                claimed_cells.add(best_cell)
            assignments[drone.id] = best_cell

        return assignments
