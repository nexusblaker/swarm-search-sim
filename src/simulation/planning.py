"""Small path-planning helpers used by the simulation engine and strategies."""

from __future__ import annotations

from heapq import heappop, heappush

from src.environment.grid import GridEnvironment


Position = tuple[int, int]


def astar_path(
    environment: GridEnvironment,
    start: Position,
    goal: Position,
    blocked: set[Position] | None = None,
) -> list[Position]:
    """Return an obstacle-aware path from start to goal using A*."""

    if start == goal:
        return [start]
    if environment.is_obstacle(goal):
        return [start]

    blocked = blocked or set()
    frontier: list[tuple[float, Position]] = []
    heappush(frontier, (0.0, start))
    came_from: dict[Position, Position | None] = {start: None}
    cost_so_far: dict[Position, float] = {start: 0.0}

    while frontier:
        _, current = heappop(frontier)
        if current == goal:
            break

        for neighbor in environment.get_neighbors(current, diagonal=True):
            if neighbor in blocked and neighbor != goal:
                continue
            movement_cost = environment.get_movement_cost(neighbor)
            new_cost = cost_so_far[current] + movement_cost
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                priority = new_cost + environment.estimate_cost(neighbor, goal)
                heappush(frontier, (priority, neighbor))
                came_from[neighbor] = current

    if goal not in came_from:
        return [start]

    path: list[Position] = []
    current: Position | None = goal
    while current is not None:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path


def path_cost(environment: GridEnvironment, path: list[Position]) -> float:
    """Return the terrain-weighted cost of a path."""

    if len(path) <= 1:
        return 0.0
    return float(sum(environment.get_movement_cost(position) for position in path[1:]))
