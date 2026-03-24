# Swarm Search Sim

Swarm Search Sim is a modular Python platform for research-oriented multi-drone search coordination under uncertainty. Phase 4 upgrades the existing simulator into a belief-driven autonomy core with entropy-aware planning, hierarchical coordination, external map-layer ingestion, and replayable experiment artifacts.

## Phase 4 Capabilities

- belief-state target tracking with motion propagation and positive/negative evidence updates
- entropy-aware uncertainty maps and expected information-gain utilities
- terrain-aware A* routing with obstacles, slope penalties, trails, and wind effects
- communication radius, packet loss, latency, and centralized or decentralized coordination
- battery-aware return-to-base behavior with forced-return tracking
- multiple target behavior modes:
  - `random_walk`
  - `terrain_biased`
  - `trail_biased`
  - `injured_slow`
  - `stationary_intervals`
- multi-channel lightweight sensing with thermal plus visual-proxy fusion
- five coordination strategies:
  - `random_sweep`
  - `sector_search`
  - `probability_greedy`
  - `auction_based`
  - `information_gain`
- hierarchical coordination where global objectives are assigned and local path planning executes them
- event logging and replay artifact export for completed runs
- grouped robustness experiments across scenario families, comms modes, battery budgets, and sensor modes

## Current Architecture

- `src/scenarios/scenario.py`: `ScenarioConfig`, YAML parsing, scenario-family presets, Phase 4 config fields
- `src/environment/grid.py`: synthetic generation, external layer loading, terrain costs, trails, elevation, wind, LOS helpers
- `src/agents/drone.py`: drone state, local/shared knowledge, path history, battery and return state
- `src/probability/heatmap.py`: probability-map compatibility layer, suppression and diffusion helpers
- `src/probability/belief.py`: belief-state propagation, entropy maps, expected information gain
- `src/sensors/thermal.py`: thermal plus visual-proxy footprint sensing with weather and LOS effects
- `src/coordination/`: shared strategy interface plus five strategy implementations
- `src/simulation/planning.py`: reusable A* path planning helper
- `src/simulation/engine.py`: mission loop, target motion, belief updates, comms queue, routing, metrics, event logging, replay history
- `src/visualisation/renderer.py`: terrain, belief heatmap, trails, scan footprints, comm links, objectives, reserved paths
- `benchmark.py`: standard benchmark plus grouped Phase 4 experiment runner
- `data/sample_layers/`: lightweight CSV terrain, obstacle, trail, elevation, and wind layers

## Belief-State and Information-Gain Model

- The simulator maintains a normalized belief distribution over target location.
- Belief is propagated every step using a configurable motion model tied to the selected target behavior mode.
- Negative scans suppress belief over the observed footprint, while repeated scans suppress local belief more strongly.
- Positive detections contribute soft evidence that sharpens the belief peak over time.
- Entropy is derived from the belief state and exposed to strategies.
- The `information_gain` strategy scores candidate objectives using expected uncertainty reduction, route cost, battery state, and overlap penalties.

## Comms and Battery Constraints

- In `centralized` mode, drones synchronize through the base station.
- In `decentralized` mode, drones exchange state directly when within communication range.
- Packet loss and latency delay belief sharing, searched-cell updates, and teammate intent.
- Drones track stale information windows, and poor comms measurably degrade coordination quality.
- Drones trigger return-to-base when their remaining battery is no longer safe relative to the planned path home plus the configured return threshold.

## External Scenario Layers

The simulator can run on synthetic terrain or on externally defined map layers.

Supported layer types:

- terrain layer
- obstacle layer
- trail layer
- elevation layer
- optional wind layer

The default repo includes a lightweight example under `data/sample_layers/`. You can point `configs/default.yaml` at your own `.csv`, `.json`, or `.npy` layer files using `layer_paths`.

## Run One Simulation

From the repo root:

```bash
python main.py
```

Outputs are written under `outputs/`:

- `final_state.png`
- `frames/`
- `run_events.jsonl`
- `run_replay.json`

## Run Benchmarks and Experiments

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
- `plot_entropy_reduction_by_strategy.png`
- `plot_confirmed_detection_time_by_strategy.png`
- `plot_coordination_efficiency_vs_drone_count.png`

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
- `entropy_reduction_over_time`
- `information_gain_per_step`
- `belief_peak_accuracy`
- `time_to_first_candidate_detection`
- `time_to_confirmed_detection`
- `false_alarm_count`
- `reroute_count`
- `coordination_efficiency`
- `return_to_base_efficiency`
- `mission_success`

## Tests

Run the test suite from the repo root:

```bash
pytest
```

The current tests cover:

- belief normalization after propagation and evidence updates
- external map layer loading
- information-gain and hierarchical-coordination smoke execution
- low-battery return behavior
- communication degradation effects
- event logging and replay artifact creation
- benchmark and grouped experiment outputs
- A* validity on the layered map
