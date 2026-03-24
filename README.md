# Swarm Search Sim

Swarm Search Sim is a modular local mission planning and review platform for multi-drone search coordination under uncertainty. The `src/` package remains the simulation core, while Phase 5 adds product-facing backend and frontend layers for scenario management, mission execution, replay, experiments, operator interventions, and report generation.

## Product Architecture

### Simulation Core

- `src/scenarios/scenario.py`: scenario configuration and family presets
- `src/environment/grid.py`: terrain, obstacle, trail, elevation, and wind support
- `src/probability/heatmap.py`: compatibility probability-map layer
- `src/probability/belief.py`: belief-state propagation, entropy, and information gain
- `src/coordination/`: five coordination strategies plus shared interfaces
- `src/simulation/planning.py`: terrain-aware A* path planning
- `src/simulation/engine.py`: belief-driven mission loop, comms, battery policy, interventions, replay history
- `src/visualisation/renderer.py`: terrain, belief heatmap, replay, and artifact rendering

### Product Layer

- `app/backend/server.py`: thin local JSON API
- `app/backend/services.py`: scenario, mission, experiment, and report services
- `app/backend/reporting.py`: HTML mission report generation
- `app/frontend/app.py`: local mission dashboard UI
- `app/storage/`: saved scenarios, mission runs, experiments, and reports

## Phase 5 Capabilities

- local backend API for scenarios, mission runs, replay, events, experiments, and reports
- saved scenario management with YAML-compatible payloads
- mission dashboard support for live run status and snapshot polling
- local frontend for:
  - scenario editing
  - mission launch and monitoring
  - replay browsing
  - experiment browsing
- operator-in-the-loop controls:
  - pause and resume
  - force return-to-base
  - manual waypoint assignment
  - priority zone assignment
  - exclusion zone assignment
  - strategy switching
- mission summary report export to HTML
- organized local storage for scenarios, runs, experiments, and reports

## Storage Layout

Phase 5 keeps the legacy `outputs/` artifacts intact and adds product storage under `app/storage/`:

- `app/storage/scenarios/`
- `app/storage/runs/<run_id>/`
- `app/storage/experiments/<experiment_id>/`
- `app/storage/reports/<run_id>.html`

## Run the Core Simulator

From the repo root:

```bash
python main.py
```

This still runs the core simulator directly and writes artifacts under `outputs/`.

## Run the Backend API

From the repo root:

```bash
python -m app.backend.server --host 127.0.0.1 --port 8000
```

Useful API routes:

- `GET /api/health`
- `GET /api/presets`
- `GET /api/scenarios`
- `POST /api/scenarios`
- `GET /api/scenarios/{scenario_id}`
- `POST /api/runs`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/replay`
- `GET /api/runs/{run_id}/events`
- `POST /api/runs/{run_id}/interventions`
- `POST /api/runs/{run_id}/report`
- `POST /api/experiments`
- `GET /api/experiments`
- `GET /api/experiments/{experiment_id}`
- `GET /api/experiments/{experiment_id}/summary`

## Run the Frontend

The local MVP frontend is implemented with Streamlit so it runs cleanly in this environment without a Node toolchain.

From the repo root:

```bash
python -m streamlit run app/frontend/app.py
```

If your backend is not on the default port, set:

```bash
set SWARM_API_BASE_URL=http://127.0.0.1:8000
```

Then start the frontend.

## Using the Scenario Editor

In the frontend:

1. Open `Scenarios`.
2. Load an existing scenario or start with defaults.
3. Edit:
   - map size and family
   - layer paths
   - drone count and specs
   - strategy
   - comms settings
   - battery threshold
   - target behavior
   - sensor settings
   - belief and planner settings
4. Save the scenario.

Validation is currently handled through constrained numeric inputs and bounded select options.

## Running Missions

In the frontend:

1. Open `Mission Run`.
2. Choose a saved scenario.
3. Launch a mission.
4. Poll the latest state, metrics, and artifacts.
5. Use operator controls to:
   - pause or resume
   - force a drone return
   - assign a waypoint
   - create priority or exclusion zones
   - switch strategy

All interventions are recorded in the event log and replay history.

## Replay and Review

In the frontend:

1. Open `Replay`.
2. Select a completed or in-progress run.
3. Scrub through the replay timeline.
4. Inspect step-by-step mission state and the events that occurred at each step.

Replay data is sourced directly from the generated `run_replay.json` and `run_events.jsonl` artifacts.

## Experiments and Benchmarks

The core benchmark entrypoint still works:

```bash
python benchmark.py
```

You can also launch smaller experiment batches from the frontend or via `POST /api/experiments`.

Experiment outputs include:

- raw benchmark CSVs
- grouped experiment CSVs
- summary CSVs
- comparison plots

## Report Generation

Mission reports can be generated from the frontend or via:

```bash
POST /api/runs/{run_id}/report
```

The current HTML report includes:

- scenario metadata
- strategy and run summary
- metrics table
- key event counts
- artifact references
- event timeline samples

## Tests

Run the full suite from the repo root:

```bash
pytest
```

Current coverage includes:

- belief normalization and Phase 4 simulation behavior
- local API smoke tests
- scenario save and load
- mission run request flow
- replay and event fetch flow
- operator intervention handling
- report generation
- experiment artifact creation
