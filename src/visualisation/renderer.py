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
        searched_cells = list(snapshot.get("searched_cells", []))
        drone_positions = [tuple(drone["position"]) for drone in snapshot["drones"]]
        drone_trails = [list(drone.get("path_history", [])) for drone in snapshot["drones"]]
        target_position = tuple(snapshot["target_position"])
        target_trail = list(snapshot.get("target_trail", []))
        detection_event = snapshot.get("detection_event")
        obstacle_mask = np.asarray(snapshot.get("obstacle_mask"))

        fig, ax = plt.subplots(figsize=(10, 7))
        ax.imshow(terrain_grid, cmap=SimulationRenderer.TERRAIN_CMAP, origin="upper")
        if obstacle_mask.size:
            obstacle_overlay = np.ma.masked_where(~obstacle_mask, obstacle_mask)
            ax.imshow(obstacle_overlay, cmap="gray_r", alpha=0.35, origin="upper")
        heatmap = ax.imshow(
            probability_map,
            cmap="inferno",
            alpha=0.55,
            origin="upper",
        )
        fig.colorbar(heatmap, ax=ax, fraction=0.046, pad=0.04, label="Target probability")

        if searched_cells:
            searched_x = [cell[0] for cell in searched_cells]
            searched_y = [cell[1] for cell in searched_cells]
            ax.scatter(
                searched_x,
                searched_y,
                s=10,
                c="#ffd166",
                alpha=0.16,
                marker="s",
                label="Searched region",
            )

        if visited_cells:
            visited_x = [cell[0] for cell in visited_cells]
            visited_y = [cell[1] for cell in visited_cells]
            ax.scatter(visited_x, visited_y, s=12, c="#ffffff", alpha=0.35, marker="s", label="Visited")

        for trail in drone_trails:
            if len(trail) < 2:
                continue
            trail_x = [position[0] for position in trail]
            trail_y = [position[1] for position in trail]
            ax.plot(trail_x, trail_y, color="#4cc9f0", linewidth=1.2, alpha=0.5)

        if drone_positions:
            drone_x = [position[0] for position in drone_positions]
            drone_y = [position[1] for position in drone_positions]
            ax.scatter(drone_x, drone_y, s=100, c="#00bcd4", edgecolors="black", label="Drones")

        if len(target_trail) >= 2:
            target_x = [position[0] for position in target_trail]
            target_y = [position[1] for position in target_trail]
            ax.plot(target_x, target_y, color="#ff6b6b", linewidth=1.4, linestyle="--", alpha=0.7, label="Target trail")

        ax.scatter(
            [target_position[0]],
            [target_position[1]],
            s=120,
            c="#ff3366",
            marker="*",
            edgecolors="black",
            label="Target",
        )
        if detection_event is not None:
            detected_position = tuple(detection_event["position"])
            detection_marker = plt.Circle(detected_position, radius=1.0, fill=False, color="#80ed99", linewidth=2.0)
            ax.add_patch(detection_marker)
            ax.text(
                detected_position[0] + 0.6,
                detected_position[1] - 0.6,
                "Detected",
                color="#80ed99",
                fontsize=9,
                weight="bold",
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

    @staticmethod
    def render_frames(
        history: list[dict[str, Any]],
        output_dir: str | Path,
        step_stride: int = 1,
    ) -> list[Path]:
        """Render a sequence of snapshots to a frame directory."""

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        frame_paths: list[Path] = []
        stride = max(step_stride, 1)
        for index, snapshot in enumerate(history[::stride]):
            frame_path = output_path / f"frame_{index:04d}.png"
            SimulationRenderer.render_static(snapshot, output_path=frame_path, show=False)
            frame_paths.append(frame_path)
        return frame_paths
