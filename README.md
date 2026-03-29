# Swarm Search Sim

Swarm Search Sim is a local mission planning and evaluation platform for multi-drone search-and-rescue teams. The simulation core stays under `src/`, while the product-facing planning, comparison, review, reporting, and history workflows live under `app/`.

Phase 7 upgrades the platform from run-centric decision support into a plan-centric workflow with first-class mission plans, saved plan comparisons, after-action review, richer scenario library metadata, and cleaner backend service seams.

## Phase 7 Architecture

### Simulation Core

- `src/scenarios/scenario.py`: mission configuration and scenario-family presets
- `src/environment/grid.py`: terrain, obstacle, trail, elevation, and wind support
- `src/probability/belief.py`: belief propagation, entropy, and information gain
- `src/coordination/`: coordination strategies and shared interfaces
- `src/simulation/planning.py`: terrain-aware A* routing
- `src/simulation/engine.py`: mission loop, sensing, comms, battery policy, interventions, replay history
- `src/visualisation/renderer.py`: terrain and belief rendering for artifacts and replay

### Product Backend

- `app/backend/main.py`: FastAPI entrypoint
- `app/backend/api/`: route groups for scenarios, plans, comparisons, runs, reviews, reports, experiments, jobs, and recommendations
- `app/backend/domain/`: domain services split by seam
  - `scenarios.py`
  - `plans.py`
  - `comparisons.py`
  - `runs.py`
  - `experiments.py`
  - `reviews.py`
  - `reports.py`
  - `recommendations.py`
- `app/backend/services.py`: thin composition layer
- `app/backend/db/sqlite.py`: SQLite metadata and linkage model
- `app/backend/core/job_manager.py`: local background jobs
- `app/backend/core/templates.py`: operational scenario library presets
- `app/backend/reporting.py`: HTML report generation

### Product Frontend

- `app/frontend/app.py`: Streamlit home page
- `app/frontend/pages/`: operator-facing planning and evaluation views
- `app/frontend/common.py`: shared API helpers, tables, and scenario/plan builders
- `app/frontend/api_client.py`: thin client for the FastAPI backend

## Phase 7 Product Workflow

The intended operator flow is now:

1. Create or select a scenario or scenario-library template.
2. Build a `MissionPlan` on top of that baseline.
3. Save a `PlanComparison` workspace to compare candidate plans.
4. Launch a run from a mission plan or from a saved comparison candidate.
5. Monitor the mission, apply interventions if needed, and inspect replay.
6. Generate an `AfterActionReview` from the completed run.
7. Use reports and indexed artifacts for review, documentation, and plan iteration.

## First-Class Product Objects

### Mission Plans

`MissionPlan` is now a first-class backend entity stored in SQLite. A mission plan can include:

- plan name
- linked scenario or template
- selected strategy
- drone / asset package
- reserve policy
- communication assumptions
- map or layer selection
- priority zones
- exclusion zones
- candidate alternatives
- operator notes
- recommendation snapshot
- approval state
- linkage to runs, comparisons, and reviews

### Saved Plan Comparisons

Plan comparison is no longer only a transient endpoint. Saved comparisons now store:

- parent mission plan
- named candidate plans
- ranked results
- sensitivity summary
- uncertainty bands
- recommendation snapshot
- linkage to launched runs

### After-Action Review

After-action review is now a product workflow and stored entity. A review includes:

- mission timeline
- key interventions
- detection timeline
- actual mission outcome
- deviation from recommendation
- battery and comms risk summary
- asset utilization summary
- alternate-plan summary when a saved comparison exists

## Scenario Library

The operational library extends the old demo templates with richer metadata:

- doctrine type
- intended use
- recommended strategies
- risks
- assumptions
- tags

Included presets now include:

- Open Terrain Rescue
- Dense Canopy Poor Comms
- Windy Ridge-Line Search
- Low Battery Contingency
- Staged Sector Sweep
- Rapid Containment
- Obstacle Heavy Search

## SQLite and Product Storage

Artifacts remain file-based. SQLite indexes metadata, state, summaries, and linkage between objects.

Default local storage:

- `app/storage/swarm_product.db`
- `app/storage/scenarios/`
- `app/storage/templates/`
- `app/storage/plans/`
- `app/storage/comparisons/`
- `app/storage/runs/<run_id>/`
- `app/storage/experiments/<experiment_id>/`
- `app/storage/reviews/`
- `app/storage/reports/<report_id>.html`

## Run the Core Simulator

From the repo root:

```bash
python main.py
```

This still runs the simulator directly and writes core artifacts under `outputs/`.

## Run the FastAPI Backend

From the repo root:

```bash
python -m app.backend.server --host 127.0.0.1 --port 8000
```

Or:

```bash
uvicorn app.backend.main:app --host 127.0.0.1 --port 8000
```

FastAPI docs:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## Run the Streamlit Frontend

From the repo root:

```bash
python -m streamlit run app/frontend/app.py
```

If needed, point Streamlit at a non-default backend:

```bash
set SWARM_FRONTEND_API_BASE_URL=http://127.0.0.1:8000
```

## Main API Endpoints

### Health

- `GET /health`

### Scenarios

- `GET /scenarios`
- `POST /scenarios`
- `GET /scenarios/{id}`
- `PUT /scenarios/{id}`
- `DELETE /scenarios/{id}`

### Mission Plans

- `GET /plans`
- `POST /plans`
- `GET /plans/{id}`
- `PUT /plans/{id}`
- `DELETE /plans/{id}`

### Saved Comparisons

- `GET /comparisons`
- `POST /comparisons`
- `GET /comparisons/{id}`
- `POST /comparisons/{id}/run`
- `GET /comparisons/{id}/summary`

### Runs

- `POST /runs`
- `GET /runs`
- `GET /runs/{id}`
- `POST /runs/{id}/interventions`
- `GET /runs/{id}/replay`
- `GET /runs/{id}/events`

### Reviews

- `GET /reviews`
- `POST /reviews`
- `GET /reviews/{id}`
- `POST /reviews/from-run/{run_id}`

### Scenario Library

- `GET /library/templates`
- `GET /library/templates/{id}`

### Experiments

- `POST /experiments`
- `GET /experiments`
- `GET /experiments/{id}`
- `GET /experiments/{id}/summary`

### Reports

- `GET /reports`
- `POST /reports/{run_id}`
- `GET /reports/{id}`

### Decision Support

- `POST /compare-plans`
- `POST /recommend`

### Jobs

- `GET /jobs`
- `GET /jobs/{id}`
- `POST /jobs/{id}/cancel`

## Decision Support Outputs

Recommendations and comparisons now expose richer mission-facing summaries such as:

- uncertainty bands
- battery margin risk
- communications fragility
- overlap inefficiency
- failure mode summaries
- robustness under changed assumptions
- recommendation rationale

These outputs remain lightweight and explainable. This phase does not introduce heavy ML or autonomous control logic.

## Streamlit Pages

The frontend now centers the planning and evaluation workflow:

- Scenarios
- Mission Plans
- Scenario Library
- Plan Comparison
- Recommendations
- Mission Control
- Replay
- Run History
- Experiments
- Reports
- After-Action Review

## Testing

Run the full suite from the repo root:

```bash
pytest
```

The test suite covers:

- simulation smoke behavior
- FastAPI smoke and docs
- scenario CRUD
- mission plan CRUD
- saved comparison workflows
- launching runs from plans and comparisons
- replay and event retrieval
- after-action review generation
- scenario library retrieval
- report indexing
- experiment history flow

## Local Deployment

Environment guidance lives in `.env.example`.

Local container workflow:

```bash
docker-compose up --build
```

This keeps the product local-first and lightweight while preserving the simulator and product workflows from the repo root.
