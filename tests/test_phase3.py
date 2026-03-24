"""Phase 3 integration and behavior tests."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from benchmark import run_benchmarks, run_grouped_experiments
from src.environment.grid import GridEnvironment
from src.probability.heatmap import ProbabilityMap
from src.simulation.engine import SimulationEngine
from src.simulation.planning import astar_path
from src.utils.config_loader import load_scenario_config


def test_astar_returns_valid_path_around_obstacles() -> None:
    terrain = np.zeros((6, 6), dtype=int)
    movement_cost = np.ones((6, 6), dtype=float)
    detection_modifier = np.ones((6, 6), dtype=float)
    obstacle_mask = np.zeros((6, 6), dtype=bool)
    obstacle_mask[1:5, 2] = True
    obstacle_mask[3, 2] = False
    environment = GridEnvironment(terrain, movement_cost, detection_modifier, obstacle_mask)

    path = astar_path(environment, start=(0, 0), goal=(5, 5))

    assert path[0] == (0, 0)
    assert path[-1] == (5, 5)
    assert all(not environment.is_obstacle(cell) for cell in path)


def test_probability_map_remains_normalized_after_repeated_updates() -> None:
    rng = np.random.default_rng(5)
    environment = GridEnvironment.generate(width=20, height=16, rng=rng, obstacle_ratio=0.05)
    probability_map = ProbabilityMap(environment.shape, last_known_position=(10, 8), sigma=4.0)
    probability_map.apply_terrain_weighting(environment)

    search_counts = {(2, 2): 3, (3, 3): 2, (4, 4): 4}
    for _ in range(6):
        probability_map.diffuse(environment, diffusion_rate=0.12)
        probability_map.update_after_negative_search(search_counts.keys(), suppression=0.18, search_counts=search_counts)

    assert np.isclose(probability_map.values.sum(), 1.0)
    assert np.all(probability_map.values >= 0.0)


def test_low_battery_drones_eventually_return_to_base() -> None:
    config = replace(
        load_scenario_config(),
        drone_battery=40.0,
        return_to_base_threshold=18.0,
        max_steps=50,
        strategy="probability_greedy",
    )
    engine = SimulationEngine(config)
    metrics = engine.run()

    assert metrics.forced_low_battery_returns >= 1
    assert any(drone.return_completed for drone in engine.drones)


def test_comms_delay_and_loss_affect_shared_state_behavior() -> None:
    config = replace(
        load_scenario_config().with_scenario_family("poor_comms"),
        max_steps=12,
        strategy="auction_based",
    )
    engine = SimulationEngine(config)
    engine.run()

    assert engine.metrics.comms_failures > 0
    assert engine.metrics.stale_information_events > 0


def test_grouped_benchmark_produces_outputs(tmp_path: Path) -> None:
    run_benchmarks(output_dir=tmp_path, num_seeds=2, strategies=["random_sweep", "information_gain"])
    grouped_results = run_grouped_experiments(
        output_dir=tmp_path,
        num_seeds=1,
        strategies=["auction_based", "information_gain"],
        scenario_families=["open_terrain", "poor_comms"],
        target_behaviors=["terrain_biased"],
        coordination_modes=["centralized", "decentralized"],
        drone_counts=[4],
    )

    assert len(grouped_results) == 8
    assert (tmp_path / "benchmark_results.csv").exists()
    assert (tmp_path / "experiment_results.csv").exists()
    assert (tmp_path / "experiment_summary.csv").exists()
    assert (tmp_path / "plot_success_by_strategy_family.png").exists()
    assert (tmp_path / "plot_time_by_strategy_comms.png").exists()
    assert (tmp_path / "plot_overlap_by_strategy.png").exists()


def test_new_strategies_run_successfully() -> None:
    base_config = load_scenario_config()
    for strategy in ["auction_based", "information_gain"]:
        engine = SimulationEngine(replace(base_config, strategy=strategy, max_steps=25))
        metrics = engine.run()
        assert metrics.area_covered_pct >= 0.0
