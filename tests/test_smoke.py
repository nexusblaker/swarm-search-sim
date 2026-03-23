"""Smoke tests for the Phase 1 simulation pipeline."""

from __future__ import annotations

from pathlib import Path

from src.simulation.engine import SimulationEngine
from src.utils.config_loader import load_scenario_config
from src.visualisation.renderer import SimulationRenderer


def test_phase1_simulation_smoke(tmp_path: Path) -> None:
    config = load_scenario_config()
    engine = SimulationEngine(config)

    metrics = engine.run()
    snapshot = engine.get_state_snapshot()
    output_path = tmp_path / "smoke_render.png"
    SimulationRenderer.render_static(snapshot, output_path=output_path, show=False)

    assert snapshot["step"] <= config.max_steps
    assert 0.0 <= metrics.area_covered_pct <= 100.0
    assert 0.0 <= metrics.probability_mass_covered <= 1.0
    assert output_path.exists()
