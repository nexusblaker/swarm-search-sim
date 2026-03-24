# Swarm Search Sim

Swarm Search Sim is a modular Python project for multi-drone search-and-rescue simulation under uncertainty. Phase 2 upgrades the original architecture into an end-to-end simulation core with dynamic target motion, terrain-aware sensing and movement, multiple coordination strategies, benchmarking, and visual outputs.

## Current Architecture

The package layout under `src/` is preserved from Phase 1:

- `src/scenarios/scenario.py`: `ScenarioConfig` and YAML-backed scenario settings
- `src/environment/grid.py`: terrain generation, movement costs, detection modifiers, obstacle masking
- `src/agents/drone.py`: drone state, path history, battery accounting, detection logs
- `src/probability/heatmap.py`: target belief initialization, terrain weighting, diffusion, negative-search suppression
- `src/sensors/thermal.py`: stochastic thermal scan model using distance, terrain, weather, false positives, and false negatives
- `src/coordination/`: `RandomSweepStrategy`, `SectorSearchStrategy`, and `ProbabilityGreedyStrategy`
- `src/analytics/metrics.py`: mission summary metrics
- `src/simulation/engine.py`: per-step mission loop, target motion, scanning, history capture, and stop conditions
- `src/visualisation/renderer.py`: final-state rendering plus saved frame generation
- `src/utils/config_loader.py`: loading `configs/default.yaml`

## Implemented Strategies

- `random_sweep`: exploration-heavy random motion with simple anti-backtracking behavior
- `sector_search`: assigns drones to vertical sectors and sweeps them systematically
- `probability_greedy`: prioritizes high-probability cells while reducing same-cell overlap

## Metrics Tracked

- `time_to_detection`
- `area_covered_pct`
- `probability_mass_covered`
- `overlap_ratio`
- `battery_used`
- `mission_success`

## Configuration

The default scenario is in `configs/default.yaml`. It currently controls:

- weather
- number of drones
- target behavior and speed
- target start radius around the last known position
- terrain ratios and obstacle rate
- drone battery, movement speed, and sensor range
- sensor false positive / false negative rates
- probability diffusion and negative-search suppression
- render frame settings
- benchmark seed count and strategy list

## Run One Simulation

From the repo root:

```bash
python main.py
```

Outputs are written under `outputs/`:

- `final_state.png`: final rendered simulation state
- `frames/`: saved step frames from the run

## Run Benchmarks

From the repo root:

```bash
python benchmark.py
```

Benchmark outputs are written under `outputs/`:

- `benchmark_results.csv`: one row per `(strategy, seed)` run
- `benchmark_summary.csv`: grouped summary statistics by strategy
- `benchmark_comparison.png`: comparison chart for average time to detection and success rate

## Tests

Run all tests from the repo root:

```bash
pytest
```

The test suite currently covers:

- a full simulation smoke test
- benchmark output generation
- probability-map normalization after repeated updates
