"""Phase 4 integration and behavior tests."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from benchmark import run_benchmarks, run_grouped_experiments
from src.environment.mission_area import (
    build_environment_from_mission_area,
    derive_mission_area_layers,
    preview_mission_area,
    resolve_location_input,
)
from src.probability.belief import BeliefState
from src.simulation.engine import SimulationEngine
from src.simulation.lifecycle import LIFECYCLE_READY, LIFECYCLE_RECHARGING, LIFECYCLE_RETURNING
from src.simulation.planning import astar_path
from src.simulation.search_patterns import (
    SearchPatternPlanner,
    estimate_search_geometry,
    recommend_search_pattern,
)
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


def test_search_pattern_recommendation_prefers_broad_sweep_for_unknown_wide_area() -> None:
    config = replace(
        load_scenario_config(),
        map_size=(30, 22),
        num_drones=4,
        mission_intent="broad_area_coverage",
        search_pattern="auto",
        last_known_status="unknown",
    )

    decision = recommend_search_pattern(config)

    assert decision.pattern == "broad_area_sweep"
    assert "wide" in decision.reason.lower() or "uncertain" in decision.reason.lower()


def test_search_geometry_lane_spacing_grows_with_sensor_swath() -> None:
    base = replace(load_scenario_config(), sensor_range=4.0)
    wide = replace(load_scenario_config(), sensor_range=8.0)

    base_geometry = estimate_search_geometry(base)
    wide_geometry = estimate_search_geometry(wide)

    assert wide_geometry.effective_swath_cells > base_geometry.effective_swath_cells
    assert wide_geometry.lane_spacing_cells > base_geometry.lane_spacing_cells


def test_mission_area_preview_builds_deterministic_real_grid_layers() -> None:
    location = resolve_location_input(query="Katoomba")
    mission_area = preview_mission_area(
        location=location,
        grid_resolution_m=400.0,
        environment_type="dense_forest",
        weather="windy",
    )
    layers = derive_mission_area_layers(
        mission_area,
        scenario_family="dense_forest",
        weather="windy",
    )
    environment = build_environment_from_mission_area(
        mission_area,
        scenario_family="dense_forest",
        weather="windy",
    )

    assert mission_area["location_display_name"] == "Katoomba, NSW"
    assert mission_area["grid_size"][0] >= 12
    assert mission_area["grid_size"][1] >= 10
    assert mission_area["terrain_summary"]["dominant_terrain"]
    assert mission_area["staging"]["grid_position"]
    assert layers["terrain_grid"].shape == environment.shape
    assert layers["elevation_layer"].shape == environment.shape
    assert layers["terrain_summary"]["operator_summary"]
    assert np.isfinite(layers["wind_layer"]).all()


def test_low_battery_drones_eventually_return_to_base() -> None:
    config = replace(
        load_scenario_config(),
        drone_battery=40.0,
        return_to_base_threshold=18.0,
        max_steps=50,
        strategy="probability_greedy",
        false_negative_rate=1.0,
        visual_false_negative_rate=1.0,
        false_positive_rate=0.0,
    )
    engine = SimulationEngine(config)
    metrics = engine.run()

    assert metrics.forced_low_battery_returns >= 1
    assert metrics.successful_returns_to_base >= 1
    assert any(event["event_type"] == "battery_service_started" for event in engine.logger.events)


def test_cue_requires_inspection_before_confirmation() -> None:
    config = replace(
        load_scenario_config(),
        max_steps=8,
        num_drones=1,
        false_positive_rate=0.0,
        false_negative_rate=0.0,
        visual_false_negative_rate=0.0,
        target_move_probability=0.0,
        weather="clear",
    )
    engine = SimulationEngine(config)
    drone = engine.drones[0]
    anchor = engine._resolve_open_cell((2, 2))
    target = anchor
    drone.position = anchor
    drone.path_history = [anchor]
    drone.visited_cells = {anchor}
    drone.local_known_visited = {anchor}
    engine.target.position = target
    engine.target.path_history = [target]
    engine.environment.detection_modifier[target[1], target[0]] = 1.0
    engine.manual_targets[drone.id] = anchor

    first = engine.step()

    assert not first["done"]
    assert not engine.target.detected
    assert any(event["event_type"] == "possible_contact_detected" for event in engine.logger.events)
    assert first["candidate_contacts"]
    assert first["candidate_contacts"][0]["status"] == "cue_detected"

    second = engine.step()

    assert any(event["event_type"] == "inspection_initiated" for event in engine.logger.events)
    assert second["drones"][0]["assigned_contact_id"] is not None
    assert second["run_phase"] in {"Inspecting possible contact", "Possible contact detected", "Target confirmed"}


def test_false_positive_contact_is_rejected_and_search_resumes() -> None:
    config = replace(
        load_scenario_config(),
        max_steps=10,
        num_drones=1,
        false_positive_rate=1.0,
        false_negative_rate=1.0,
        visual_false_negative_rate=1.0,
        target_move_probability=0.0,
    )
    engine = SimulationEngine(config)
    drone = engine.drones[0]
    anchor = engine._resolve_open_cell((3, 3))
    drone.position = anchor
    drone.path_history = [anchor]
    drone.visited_cells = {anchor}
    drone.local_known_visited = {anchor}
    engine.manual_targets[drone.id] = anchor

    for _ in range(6):
        engine.step()
        if any(event["event_type"] == "false_positive_rejected" for event in engine.logger.events):
            break

    event_types = {event["event_type"] for event in engine.logger.events}

    assert "possible_contact_detected" in event_types
    assert "inspection_initiated" in event_types
    assert "false_positive_rejected" in event_types
    assert "search_resumed_after_reject" in event_types
    assert not engine.target.detected


def test_reserve_preset_changes_point_of_no_return_margin() -> None:
    config = replace(load_scenario_config(), max_steps=1, num_drones=1)
    aggressive_engine = SimulationEngine(replace(config, reserve_preset="aggressive"))
    conservative_engine = SimulationEngine(replace(config, reserve_preset="conservative"))

    aggressive_drone = aggressive_engine.drones[0]
    aggressive_drone.position = aggressive_engine._resolve_open_cell((8, 8))
    conservative_drone = conservative_engine.drones[0]
    conservative_drone.position = conservative_engine._resolve_open_cell((8, 8))
    goal = aggressive_engine._resolve_open_cell((10, 8))

    aggressive_baseline = aggressive_engine._evaluate_battery_decision(aggressive_drone, goal)
    conservative_baseline = conservative_engine._evaluate_battery_decision(conservative_drone, goal)
    shared_battery = (aggressive_baseline.continue_required + conservative_baseline.continue_required) / 2.0

    aggressive_drone.battery = shared_battery
    conservative_drone.battery = shared_battery
    aggressive = aggressive_engine._evaluate_battery_decision(aggressive_drone, goal)
    conservative = conservative_engine._evaluate_battery_decision(conservative_drone, goal)

    assert conservative.reserve_required > aggressive.reserve_required
    assert conservative.continue_required > aggressive.continue_required
    assert not aggressive.should_return
    assert conservative.should_return


def test_return_decision_uses_route_energy_not_flat_threshold() -> None:
    config = replace(load_scenario_config().with_scenario_family("layered_demo"), max_steps=1, num_drones=1)
    engine = SimulationEngine(config)
    drone = engine.drones[0]
    drone.position = engine._resolve_open_cell((10, 10))
    goal = engine._resolve_open_cell((10, 9))

    decision = engine._evaluate_battery_decision(drone, goal)
    path_home = astar_path(engine.environment, drone.position, drone.base_position)

    assert len(path_home) > 1
    assert decision.energy_to_base == pytest.approx(engine._route_energy_cost(path_home), abs=1e-3)
    assert decision.energy_to_base > 0.0
    assert decision.energy_to_base != pytest.approx(engine._distance(drone.position, drone.base_position))


def test_battery_policy_prevents_unsafe_overextension() -> None:
    config = replace(load_scenario_config(), max_steps=1, num_drones=1, reserve_preset="balanced")
    engine = SimulationEngine(config)
    drone = engine.drones[0]
    drone.position = engine._resolve_open_cell((8, 8))
    goal = engine._resolve_open_cell((10, 8))

    baseline = engine._evaluate_battery_decision(drone, goal)
    drone.battery = max(0.5, baseline.continue_required - 0.25)
    decision = engine._evaluate_battery_decision(drone, goal)
    resolved = engine._apply_battery_policy({drone.id: goal})

    assert decision.should_return
    assert resolved[drone.id] == drone.base_position
    assert drone.returning_to_base
    assert drone.lifecycle_state == LIFECYCLE_RETURNING


def test_force_return_cycle_records_recharge_and_redeploy_events() -> None:
    config = replace(
        load_scenario_config(),
        max_steps=18,
        num_drones=1,
        turnaround_time_minutes=2.0,
        step_duration_minutes=1.0,
        false_negative_rate=1.0,
        visual_false_negative_rate=1.0,
        false_positive_rate=0.0,
    )
    engine = SimulationEngine(config)
    drone = engine.drones[0]
    repositioned = engine._resolve_open_cell((5, 5))
    drone.position = repositioned
    drone.path_history.append(repositioned)
    drone.visited_cells.add(repositioned)
    drone.local_known_visited.add(repositioned)

    engine.apply_intervention("force_return", {"drone_id": 0})
    seen_states: set[str] = set()
    for _ in range(12):
        engine.step()
        seen_states.add(engine.drones[0].lifecycle_state)
        if engine.drones[0].redeployments > 0:
            break

    event_types = {event["event_type"] for event in engine.logger.events}

    assert LIFECYCLE_RETURNING in seen_states
    assert LIFECYCLE_RECHARGING in seen_states
    assert LIFECYCLE_READY in seen_states or engine.drones[0].redeployments > 0
    assert engine.drones[0].redeployments >= 1
    assert {"return_to_base", "battery_service_started", "battery_service_completed", "drone_redeployed"} <= event_types


def test_engine_snapshot_and_events_expose_search_pattern_state() -> None:
    config = replace(
        load_scenario_config(),
        max_steps=6,
        search_pattern="broad_area_sweep",
        last_known_status="unknown",
        false_positive_rate=0.0,
        false_negative_rate=1.0,
        visual_false_negative_rate=1.0,
    )
    engine = SimulationEngine(config)
    snapshot = engine.step()

    event_types = {event["event_type"] for event in engine.logger.events}

    assert snapshot["search_pattern_label"] == "Broad Area Sweep"
    assert "search_pattern_geometry" in snapshot
    assert "search_pattern_selected" in event_types


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
