# Swarm Search Sim

Swarm Search Sim is a modular Python platform for research-oriented multi-drone search coordination under uncertainty. Phase 3 extends the Phase 2 prototype with reusable path planning, communication constraints, battery-aware routing, richer evidence updates, new coordination strategies, and grouped robustness experiments.

## Phase 3 Capabilities

- obstacle-aware A* path planning with terrain movement costs
- configurable communication radius, packet loss, latency, and centralized/decentralized coordination modes
- battery-aware return-to-base behavior with forced-return tracking
- richer probability suppression using repeated scan evidence
- multiple target behaviors:
  - `random_walk`
  - `terrain_biased`
  - `trail_biased`
  - `injured_slow`
  - `stationary_intervals`
- richer thermal scan footprints using range, FOV, and line-of-sight approximation
- five coordination strategies:
  - `random_sweep`
  - `sector_search`
  - `probability_greedy`
  - `auction_based`
  - `information_gain`

## Current Architecture

The Phase 2 package layout is preserved:

- `src/scenarios/scenario.py`: `ScenarioConfig`, YAML parsing, scenario-family presets
- `src/environment/grid.py`: terrain generation, obstacles, movement cost, detection modifier, LOS helpers
- `src/agents/drone.py`: drone state, path history, local/shared knowledge, battery and return state
- `src/probability/heatmap.py`: initialization, terrain weighting, diffusion, repeated-evidence suppression
- `src/sensors/thermal.py`: thermal scan model with weather, FOV, and LOS-aware footprinting
- `src/coordination/`: strategy interface plus five strategies
- `src/simulation/planning.py`: small reusable A* helper
- `src/simulation/engine.py`: mission loop, path planning, comms queue, evidence updates, returns, metrics, history
- `src/visualisation/renderer.py`: static renders, overlays, communication links, reserved paths, frame export
- `benchmark.py`: standard benchmark plus grouped robustness experiments

## Comms and Battery Model

- Drones share visited cells, searched cells, probability updates, and intended targets only when communication succeeds.
- In `centralized` mode, drones sync through the base station.
- In `decentralized` mode, drones exchange updates directly with neighbors in communication range.
- Packet loss and latency can make drone knowledge stale, which degrades coordination.
- Drones switch into return-to-base mode when remaining battery is no longer safe relative to the planned path home plus the configured threshold.

## Run One Simulation

From the repo root:

```bash
python main.py
```

Outputs are written under `outputs/`:

- `final_state.png`
- `frames/`

## Run Benchmarks and Grouped Experiments

From the repo root:

```bash
python benchmark.py
```

Outputs include:

- `benchmark_results.csv`
- `benchmark_summary.csv`
- `benchmark_comparison.png`
- `experiment_results.csv`
- `experiment_summary.csv`
- `plot_success_by_strategy_family.png`
- `plot_time_by_strategy_comms.png`
- `plot_overlap_by_strategy.png`

## Metrics Tracked

- `time_to_detection`
- `area_covered_pct`
- `probability_mass_covered`
- `overlap_ratio`
- `battery_used`
- `successful_returns_to_base`
- `forced_low_battery_returns`
- `comms_failures`
- `stale_information_events`
- `path_efficiency`
- `average_overlap_per_step`
- `detection_under_comms_mode`
- `mission_success`

## Tests

Run the test suite from the repo root:

```bash
pytest
```

The current tests cover:

- A* path validity around obstacles
- probability normalization after repeated evidence updates
- low-battery return behavior
- comms degradation affecting shared state
- grouped benchmark outputs
- smoke execution of the new strategies
