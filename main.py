"""Entrypoint for the Swarm Coordination Simulator Phase 1 demo."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from src.simulation.engine import SimulationEngine
from src.utils.config_loader import load_scenario_config
from src.visualisation.renderer import SimulationRenderer


def main() -> None:
    """Load the default scenario, execute it, render it, and print metrics."""

    config = load_scenario_config()
    engine = SimulationEngine(config)
    metrics = engine.run()

    output_path = Path("outputs") / "final_state.png"
    snapshot = engine.get_state_snapshot()
    SimulationRenderer.render_static(snapshot, output_path=output_path, show=False)

    print("Swarm Coordination Simulator for Search Coverage Optimization")
    print(f"Strategy: {config.strategy}")
    print(f"Weather: {config.weather}")
    print(f"Rendered final state to: {output_path.resolve()}")
    for metric_name, metric_value in asdict(metrics).items():
        print(f"{metric_name}: {metric_value}")


if __name__ == "__main__":
    main()
