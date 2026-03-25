# Swarm Search Sim

Swarm Search Sim is a modular local mission decision-support platform for multi-drone search coordination under uncertainty. The simulation core stays under `src/`. Phase 6 upgrades the product layer with a FastAPI backend, SQLite-backed metadata, background job tracking, plan comparison, recommendations, template browsing, multipage Streamlit workflows, and indexed reports.

## Phase 6 Architecture

### Simulation Core

- `src/scenarios/scenario.py`: mission configuration and scenario-family presets
- `src/environment/grid.py`: terrain, obstacle, trail, elevation, and wind support
- `src/probability/heatmap.py`: compatibility probability-map layer
- `src/probability/belief.py`: belief propagation, entropy, and information gain
- `src/coordination/`: coordination strategies and shared interfaces
- `src/simulation/planning.py`: terrain-aware A* routing
- `src/simulation/engine.py`: mission loop, belief updates, comms, battery policy, interventions, replay history
- `src/visualisation/renderer.py`: terrain and belief rendering for artifacts and replay

### Product Backend

- `app/backend/main.py`: FastAPI entrypoint
- `app/backend/api/`: route groups for health, scenarios, templates, runs, experiments, jobs, reports, and decision support
- `app/backend/services.py`: scenario, template, mission, experiment, comparison, recommendation, and report services
- `app/backend/db/sqlite.py`: SQLite metadata and artifact index
- `app/backend/core/job_manager.py`: local background job manager
- `app/backend/core/settings.py`: backend settings and environment-driven config
- `app/backend/core/templates.py`: built-in scenario templates
- `app/backend/reporting.py`: HTML report generation

### Product Frontend

- `app/frontend/app.py`: Streamlit home page
- `app/frontend/pages/`: multipage product views
- `app/frontend/common.py`: shared API, state, and rendering helpers
- `app/frontend/api_client.py`: thin client for the FastAPI backend

## What Phase 6 Adds

- FastAPI backend migration with automatic docs at `/docs`
- SQLite indexing for:
  - scenarios
  - scenario templates
  - runs
  - jobs
  - interventions
  - experiments
  - reports
  - artifacts
- background jobs for mission runs and experiments
- pre-mission plan comparison
- explainable recommendations and risk summaries
- multipage Streamlit decision-support UI
- indexed run history, experiment history, and report center
- local deployment support via Docker and `docker-compose`

## SQLite and Artifact Storage

Artifacts remain file-based on disk. SQLite stores the metadata, status, summaries, and artifact references.

Default local storage:

- `app/storage/swarm_product.db`
- `app/storage/scenarios/`
- `app/storage/templates/`
- `app/storage/runs/<run_id>/`
- `app/storage/experiments/<experiment_id>/`
- `app/storage/reports/<report_id>.html`

The legacy `outputs/` directory still works for direct simulator runs and benchmark scripts.

## Run the Core Simulator

From the repo root:

```bash
python main.py
```

This still runs the simulator directly and writes artifacts under `outputs/`.

## Run the FastAPI Backend

From the repo root:

```bash
python -m app.backend.server --host 127.0.0.1 --port 8000
```

Or directly with Uvicorn:

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

If needed, point the frontend at a non-default backend:

```bash
set SWARM_FRONTEND_API_BASE_URL=http://127.0.0.1:8000
```

Then start Streamlit.

## FastAPI Endpoints

### Health

- `GET /health`

### Scenarios

- `GET /scenarios`
- `POST /scenarios`
- `GET /scenarios/{id}`
- `PUT /scenarios/{id}`
- `DELETE /scenarios/{id}`

### Templates

- `GET /templates`
- `GET /templates/{id}`

### Runs

- `POST /runs`
- `GET /runs`
- `GET /runs/{id}`
- `POST /runs/{id}/interventions`
- `GET /runs/{id}/replay`
- `GET /runs/{id}/events`

### Experiments

- `POST /experiments`
- `GET /experiments`
- `GET /experiments/{id}`
- `GET /experiments/{id}/summary`

### Jobs

- `GET /jobs`
- `GET /jobs/{id}`
- `POST /jobs/{id}/cancel`

### Reports

- `GET /reports`
- `POST /reports/{run_id}`
- `GET /reports/{id}`

### Decision Support

- `POST /compare-plans`
- `POST /recommend`

## Templates and Scenario Library

Built-in templates include:

- Open Terrain Rescue
- Dense Forest Poor Comms
- Windy Ridge-Line Search
- Low Battery Mission
- Obstacle Heavy Search

Templates are browsable in the frontend and usable as launch starting points.

## Jobs and Lifecycle

Runs and experiments are executed as background jobs with statuses:

- `queued`
- `running`
- `paused`
- `completed`
- `failed`
- `cancelled`

Mission progress is updated during execution and indexed in SQLite along with the owning run or experiment.

## Plan Comparison

Plan comparison runs a lightweight short-bundle evaluation over candidate plans and compares:

- strategy
- drone count
- coordination mode
- reserve threshold

Outputs include:

- ranked candidate plans
- expected success rate
- expected detection time
- expected battery risk
- expected overlap
- top recommendation
- confidence summary

## Recommendations and Risk

Recommendations are explainable and currently use heuristic plus short-bundle comparison logic rather than a heavy ML stack. The system recommends:

- strategy
- drone count
- return-to-base reserve threshold

It also provides:

- risk summary
- overlap and battery context
- rationale for the recommendation

## Reports

Mission reports are indexed and retrievable through the backend. The HTML report includes:

- scenario metadata
- run status and strategy
- metrics table
- key event counts
- intervention timeline samples
- artifact references
- recommendation context

## Streamlit Views

The frontend is organized into these pages:

- Scenarios
- Templates
- Plan Comparison
- Recommendations
- Mission Control
- Replay
- Run History
- Experiments
- Reports

## Environment Settings

See `.env.example` for the core local settings:

- storage root
- SQLite DB path
- backend host/port
- frontend API base URL
- comparison seed count
- job worker count

## Docker

Build and run locally with Docker:

```bash
docker compose up --build
```

Services:

- backend on `8000`
- frontend on `8501`

## Tests

Run the full suite from the repo root:

```bash
pytest
```

Current coverage includes:

- Phase 4 simulation behavior
- FastAPI smoke and docs availability
- scenario CRUD
- template listing
- SQLite persistence
- job lifecycle and cancellation
- mission run and replay flow
- comparison endpoint flow
- recommendation endpoint flow
- report indexing and retrieval
- experiment history flow
