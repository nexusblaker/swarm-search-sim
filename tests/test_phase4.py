"""Phase 4 integration and behavior tests."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from benchmark import run_benchmarks, run_grouped_experiments
from src.probability.belief import BeliefState
from src.simulation.engine import SimulationEngine
from src.simulation.planning import astar_path
from src.utils.config_loader import load_scenario_config
from src.utils.event_logger import EventLogger


def test_belief_state_remains_normalized_after_propagation_and_updates() -> None:
    config = load_scenario_config()
    engine = SimulationEngine(replace(config, max_steps=5))
    belief = BeliefState(engine.environment.shape, last_known_position=(9, 7), sigma=3.5)
    belief.apply_terrain_weighting(engine.environment)

    for _ in range(4):
        belief.propagate(
            engine.environment,
            target_behavior="terrain_biased",
            motion_strength=0.2,
        )
        belief.update_from_observations(
            scanned_cells={(8, 7), (9, 7), (10, 7)},
            positive_cells={(10, 8): 0.7},
            suppression=0.18,
            positive_gain=1.5,
            search_counts={(8, 7): 2, (9, 7): 3, (10, 7): 1},
        )

    assert np.isclose(belief.values.sum(), 1.0)
    assert np.all(belief.values >= 0.0)


def test_layered_map_family_loads_external_layers_and_uses_them() -> None:
    config = load_scenario_config().with_scenario_family("layered_demo")
    engine = SimulationEngine(replace(config, max_steps=1))
    environment = engine.environment

    assert environment is not None
    assert environment.shape == (12, 12)
    assert environment.has_trail((1, 1))
    assert environment.get_wind_factor((11, 11)) > environment.get_wind_factor((0, 0))
    assert environment.get_movement_cost((1, 1)) < environment.get_movement_cost((0, 1))


def test_information_gain_strategy_and_hierarchical_objectives_run() -> None:
    config = replace(
        load_scenario_config(),
        strategy="information_gain",
        hierarchical_planning_enabled=True,
        max_steps=10,
    )
    engine = SimulationEngine(config)
    engine.step()

    assert engine.global_objectives
    assert len(engine.global_objectives) == config.num_drones
    assert engine.information_gain_history


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


def test_comms_delay_and_loss_change_shared_state_behavior() -> None:
    config = replace(
        load_scenario_config().with_scenario_family("poor_comms"),
        communication_radius=1.0,
        packet_loss_probability=0.95,
        communication_latency=0,
        max_steps=12,
        strategy="auction_based",
    )
    engine = SimulationEngine(config)
    engine.run()

    assert engine.metrics.comms_failures > 0
    assert engine.metrics.stale_information_events > 0


def test_event_logging_writes_expected_artifacts(tmp_path: Path) -> None:
    config = replace(load_scenario_config(), max_steps=8, strategy="information_gain")
    engine = SimulationEngine(config)
    engine.run()
    artifacts = engine.save_run_artifacts(tmp_path)

    assert artifacts["events"].exists()
    assert artifacts["replay"].exists()

    event_lines = artifacts["events"].read_text(encoding="utf-8").strip().splitlines()
    replay = EventLogger.load_replay(artifacts["replay"])

    assert event_lines
    assert replay
    first_event = json.loads(event_lines[0])
    assert "event_type" in first_event


def test_benchmark_and_grouped_experiments_produce_phase4_outputs(tmp_path: Path) -> None:
    run_benchmarks(
        output_dir=tmp_path,
        num_seeds=2,
        strategies=["random_sweep", "information_gain"],
    )
    grouped_results = run_grouped_experiments(
        output_dir=tmp_path,
        num_seeds=1,
        strategies=["auction_based", "information_gain"],
        scenario_families=["open_terrain", "layered_demo"],
        target_behaviors=["terrain_biased"],
        coordination_modes=["centralized"],
        drone_counts=[4],
        battery_budgets=[100.0],
        sensor_modes=["thermal_visual"],
    )

    assert len(grouped_results) == 4
    assert (tmp_path / "benchmark_results.csv").exists()
    assert (tmp_path / "benchmark_summary.csv").exists()
    assert (tmp_path / "experiment_results.csv").exists()
    assert (tmp_path / "experiment_summary.csv").exists()
    assert (tmp_path / "plot_success_by_strategy_family.png").exists()
    assert (tmp_path / "plot_time_by_strategy_comms.png").exists()
    assert (tmp_path / "plot_overlap_by_strategy.png").exists()
    assert (tmp_path / "plot_entropy_reduction_by_strategy.png").exists()
    assert (tmp_path / "plot_confirmed_detection_time_by_strategy.png").exists()
    assert (tmp_path / "plot_coordination_efficiency_vs_drone_count.png").exists()


def test_astar_returns_valid_path_on_loaded_obstacle_map() -> None:
    config = load_scenario_config().with_scenario_family("layered_demo")
    engine = SimulationEngine(replace(config, max_steps=1))
    path = astar_path(engine.environment, start=(1, 1), goal=(10, 10))

    assert path[0] == (1, 1)
    assert path[-1] == (10, 10)
    assert all(not engine.environment.is_obstacle(cell) for cell in path)
