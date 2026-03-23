"""Matplotlib renderer for simulation snapshots."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap


class SimulationRenderer:
    """Render the final or intermediate state of a mission."""

    TERRAIN_CMAP = ListedColormap(
        [
            "#d9e7b3",
            "#5b8c5a",
            "#b88b4a",
            "#9aa3b2",
            "#5ca4d6",
        ]
    )

    @staticmethod
    def render_static(
        snapshot: dict[str, Any],
        output_path: str | Path | None = None,
        show: bool = False,
    ) -> tuple[plt.Figure, plt.Axes]:
        """Render a single state snapshot and optionally save it."""

        terrain_grid = np.asarray(snapshot["terrain_grid"])
        probability_map = np.asarray(snapshot["probability_map"])
        visited_cells = list(snapshot["visited_cells"])
        drone_positions = [tuple(drone["position"]) for drone in snapshot["drones"]]
        target_position = tuple(snapshot["target_position"])

        fig, ax = plt.subplots(figsize=(10, 7))
        ax.imshow(terrain_grid, cmap=SimulationRenderer.TERRAIN_CMAP, origin="upper")
        heatmap = ax.imshow(
            probability_map,
            cmap="inferno",
            alpha=0.55,
            origin="upper",
        )
        fig.colorbar(heatmap, ax=ax, fraction=0.046, pad=0.04, label="Target probability")

        if visited_cells:
            visited_x = [cell[0] for cell in visited_cells]
            visited_y = [cell[1] for cell in visited_cells]
            ax.scatter(visited_x, visited_y, s=12, c="#ffffff", alpha=0.35, marker="s", label="Visited")

        if drone_positions:
            drone_x = [position[0] for position in drone_positions]
            drone_y = [position[1] for position in drone_positions]
            ax.scatter(drone_x, drone_y, s=100, c="#00bcd4", edgecolors="black", label="Drones")

        ax.scatter(
            [target_position[0]],
            [target_position[1]],
            s=120,
            c="#ff3366",
            marker="*",
            edgecolors="black",
            label="Target",
        )

        ax.set_title(
            f"Swarm Coordination Simulator | Step {snapshot['step']} | Strategy: {snapshot['strategy']}"
        )
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_xlim(-0.5, terrain_grid.shape[1] - 0.5)
        ax.set_ylim(terrain_grid.shape[0] - 0.5, -0.5)
        ax.legend(loc="upper right")
        fig.tight_layout()

        if output_path is not None:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(output_path, dpi=160)

        if show:
            plt.show()
        else:
            plt.close(fig)

        return fig, ax
