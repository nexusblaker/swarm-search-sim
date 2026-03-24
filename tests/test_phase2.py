"""Phase 2 integration and model tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from benchmark import run_benchmarks
from src.environment.grid import GridEnvironment
from src.probability.heatmap import ProbabilityMap
from src.simulation.engine import SimulationEngine
from src.utils.config_loader import load_scenario_config
from src.visualisation.renderer import SimulationRenderer


def test_full_simulation_smoke(tmp_path: Path) -> None:
    config = load_scenario_config()
    engine = SimulationEngine(config)

    metrics = engine.run()
    snapshot = engine.get_state_snapshot()
    render_path = tmp_path / "phase2_render.png"
    frame_dir = tmp_path / "frames"

    SimulationRenderer.render_static(snapshot, output_path=render_path, show=False)
    frame_paths = SimulationRenderer.render_frames(engine.history, output_dir=frame_dir, step_stride=2)

    assert snapshot["step"] <= config.max_steps
    assert 0.0 <= metrics.area_covered_pct <= 100.0
    assert 0.0 <= metrics.probability_mass_covered <= 1.0
    assert render_path.exists()
    assert frame_paths


def test_benchmark_runner_produces_rows(tmp_path: Path) -> None:
    results = run_benchmarks(
        output_dir=tmp_path,
        num_seeds=3,
        strategies=["random_sweep", "sector_search", "probability_greedy"],
    )

    assert len(results) == 9
    assert (tmp_path / "benchmark_results.csv").exists()
    assert (tmp_path / "benchmark_summary.csv").exists()
    assert (tmp_path / "benchmark_comparison.png").exists()


def test_probability_map_remains_normalized_after_updates() -> None:
    rng = np.random.default_rng(5)
    environment = GridEnvironment.generate(width=20, height=16, rng=rng, obstacle_ratio=0.05)
    probability_map = ProbabilityMap(environment.shape, last_known_position=(10, 8), sigma=4.0)

    probability_map.apply_terrain_weighting(environment)
    for _ in range(5):
        probability_map.diffuse(environment, diffusion_rate=0.12)
        probability_map.update_after_negative_search({(2, 2), (3, 3), (4, 4)}, suppression=0.2)

    assert np.isclose(probability_map.values.sum(), 1.0)
    assert np.all(probability_map.values >= 0.0)
