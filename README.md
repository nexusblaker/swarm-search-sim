# Swarm Search Sim

Swarm Search Sim is a modular Python simulation platform for multi-drone search-and-rescue coordination under uncertainty. Phase 1 now runs end to end from YAML config through simulation, metrics, and rendering.

## Phase 1 Architecture

The project is organized under `src/` with production-style module boundaries:

- `src/scenarios/scenario.py`: `ScenarioConfig` dataclass for scenario-level parameters.
- `src/environment/grid.py`: terrain-aware grid environment, movement costs, detection modifiers, obstacle mask.
- `src/agents/drone.py`: drone agent model and mission telemetry.
- `src/probability/heatmap.py`: gaussian probability map seeded from the last known target position.
- `src/sensors/thermal.py`: thermal detection model with weather, terrain, false positive, and false negative effects.
- `src/coordination/`: strategy interface plus `random_sweep`, `sector_search`, and `probability_greedy`.
- `src/analytics/metrics.py`: mission summary metrics.
- `src/simulation/engine.py`: orchestration layer tying the environment, drones, target, sensors, strategies, and metrics together.
- `src/visualisation/renderer.py`: static matplotlib renderer for the final state.
- `src/utils/config_loader.py`: YAML config loading from `configs/default.yaml`.

## Configuration

The default scenario lives in `configs/default.yaml` and includes:

- map size
- weather
- number of drones
- last known target position
- target assumptions
- drone defaults
- terrain generation settings
- sensor settings
- strategy and max steps

## How To Run

Create or activate your virtual environment, install dependencies, then run:

```bash
pip install -r requirements.txt
python main.py
```

This will:

1. Load `configs/default.yaml`
2. Run one simulation
3. Save a rendered final state image to `outputs/final_state.png`
4. Print summary metrics to the terminal

## Testing

Run the smoke test from the repo root:

```bash
pytest
```

The smoke test executes a full simulation run and verifies that rendering and metrics generation complete successfully.
